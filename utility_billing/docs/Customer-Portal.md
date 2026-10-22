# Customer Portal

The Rental Billing customer portal is a React single page application served at
`/rental-portal` and built from the `rental-portal` folder of this app.

## Authentication

| Flow | Implementation |
| --- | --- |
| Sign in | `frappe-react-sdk` `useFrappeAuth` (Frappe session login) |
| Sign up | standard `frappe.core.doctype.user.user.sign_up` (creates a Website User and emails a verification link) |
| Forgot password | standard `frappe.core.doctype.user.user.reset_password` |
| Change password | standard `frappe.core.doctype.user.user.update_password` |
| Logout | Frappe session logout |

The portal never stores or transmits passwords itself; every credential flow is
handled by Frappe.

Sign-up is only available when `Website Settings > Disable Signup` is unchecked.
The role granted to new sign-ups comes from `Portal Settings > Default Role`.

## Session bootstrapping

`utility_billing/www/rental-portal.py` embeds the standard Frappe session boot
(`frappe.sessions.get()`) in the page, so the SPA reads the session user and the
user's roles from `frappe.boot.user` without an extra request. The boot payload
is also what `frappe-react-sdk` uses for the session.

## Portal roles and capabilities

`utility_billing.api.portal.context.get_portal_context` resolves the *portal
role* of the session user and the capabilities granted to it:

* `Guest` – anonymous visitor, may only browse properties.
* `Tenant` – a user with the `Customer` (or `Tenant`) role that is linked to a
  Customer through the standard `Customer.portal_users` child table.
* `Property Owner` / `Landlord`, `Property Manager`, `Utility Customer` – role
  based (used by later phases).

Guests receive the `browse_properties` capability only; every authenticated
portal role currently receives all capabilities. Role specific restrictions are
introduced together with the role specific dashboards.

## Tenant to property linkage

A tenant's properties are resolved through the standard ERPNext documents:

```
User (portal_users) → Customer → Contract (party_type = Customer) → Contract.properties
```

`utility_billing.api.portal.properties.get_my_properties` returns the allocations
of those contracts, classified as:

| State | Rule |
| --- | --- |
| `Reserved` | allocation `is_active = 1` on a contract that is not signed yet (`is_signed = 0`) |
| `Active` | allocation `is_active = 1` on a signed contract, not yet ended |
| `History` | allocation `is_active = 0` or its `end_date` has passed |

## Profile, password and notification preferences

There are **no portal specific profile/settings pages**. Everything that edits a
Frappe document is handled by the generic doctype form, exactly like the desk and
the nppos dashboard:

| Task | Portal path | Backing doctype |
| --- | --- | --- |
| Profile & contact details | `/app/user/<user id>` | `User` (+ linked `Contact`) |
| Change password | `/app/user/<user id>` (Change Password section) | `User` |
| Upload profile picture | `/app/user/<user id>` | `User.user_image` / `File` |
| Notification preferences | `/app/notification-settings/<user id>` | `Notification Settings` |

The user menu ("Account") and the dashboard both link to
`/app/user/<user id>`, and the notifications feed links to
`/app/notification-settings/<user id>`.

Because `User` is a desk-only doctype, `/app/user/<user id>` resolves for users
with the corresponding permissions (System Users, e.g. staff/administrators).
A portal tenant without `User` read access is sent to the forbidden page by the
global `PermissionGuard`; granting tenants access to their own `User` record
(e.g. through a role permission with a user-permission restriction) is a
configuration decision for a later phase.

Password reset (forgot password), sign-up and login continue to use the standard
Frappe endpoints listed above — they are not doctype forms.

## API surface

| Endpoint | Guest | Purpose |
| --- | --- | --- |
| `utility_billing.api.portal.context.get_portal_context` | yes | session/role/capability bootstrap |
| `utility_billing.api.portal.properties.get_my_properties` | no | properties of the signed in tenant |
| `utility_billing.api.portal.property_details.get_property_details` | yes | a single property; own tenancy and documents when the unit is the caller's |
| `utility_billing.api.properties.get_available_properties` | yes | public property browser |

All other portal functionality (login, sign-up, password reset, password change,
profile updates, notification preferences, file upload) is served by standard
Frappe endpoints — either directly or through the generic `/app/:doctype` forms.

## Generic doctype browsing (`/app` routes)

The portal reuses the nppos dashboard approach: the generic `DocTypeList` /
`DocTypeForm` components (`src/components/doctype`, `src/components/fields`) are
driven entirely by standard Frappe endpoints, and are addressed through
slug-based routes.

| Route | Page | Standard endpoints used |
| --- | --- | --- |
| `/app/:doctype` | `DocTypeListPage` → `DocTypeList` | `frappe.desk.form.load.getdoctype`, `frappe.desk.reportview.get`, `frappe.desk.reportview.get_count` |
| `/app/:doctype/:id` (`new` for a blank form) | `DocTypeFormPage` → `DocTypeForm` | `frappe.desk.form.load.getdoc`, `frappe.client.save`, `frappe.desk.form.save.savedocs`, `frappe.model.workflow.*`, `frappe.desk.search.search_link` |

Slug ↔ doctype mapping lives in `src/lib/doctype-map.ts` (e.g.
`/app/utility-property`, `/app/contract`, `/app/user/Administrator`), with a
best-effort fallback for any doctype that is not explicitly mapped.

`DocType` records are only readable by desk users, so the command search only
offers the doctype lookup to System Users; everything else still works for any
user the individual doctype permissions allow. The user menu links a System
User's "Account" entry to `/app/user/<self>`, while tenants keep the portal
profile page. Any user who opens a page they cannot read is redirected by the
global `PermissionGuard` (403 → forbidden page).

## Notifications

* **Feed** – `/settings/notifications` reads the standard
  `frappe.desk.doctype.notification_log.notification_log.get_notification_logs`
  endpoint through `NotificationProvider` (`src/contexts/notification-context.tsx`)
  and renders the unread count, the list and a detail panel.
* **Badge** – the user menu shows the unread count from the same provider.
* **Preferences** – `/app/notification-settings/<user id>` (the user's own
  `Notification Settings` record, edited through the generic doctype form); the
  feed's *Preferences* button links straight to it.

## Command search

`⌘K` / the header search box opens the command palette
(`src/components/command-search.tsx`), which searches:

* **App Pages** – pages marked `searchable: true` in `src/config/routes.tsx`
  (the route tree is walked at runtime, so no list needs maintaining);
* **Doctypes** – `New X` / `X List` shortcuts into the `/app/:doctype` routes
  (System Users only, see above);
* **Global results** – records via `frappe.desk.reportview.get`.

## Theme customizer

The portal ships the same theme customizer as the nppos dashboard
(`src/components/theme-customizer/`):

* mounted by `BaseLayout` and opened from the user menu ("Customize Theme");
* **non modal** – the panel has no dimming overlay and does not lock scrolling,
  so the page behind stays visible and usable as a live preview; clicking
  outside the panel (or pressing Escape) closes it, and the X button is in the
  header;
* **Theme** tab – built-in property presets, the shadcn and Tweakcn preset
  families, per-mode colour and gradient editing, radius, appearance
  (light/dark) and theme import;
* **Layout** tab – sidebar variant, collapsible mode and side (drives
  `useSidebarConfig` and `useSidebar`);
* selections (preset, radius, imported theme) are persisted by the customizer
  itself in `localStorage` under `rental-portal:theme` and reapplied on load.

### Property theme engine

Theming lives in three layers:

| Layer | Location | Responsibility |
| --- | --- | --- |
| Catalogue | `src/config/theme-token-groups.ts` | every token the editor exposes, grouped (Brand, Background & Surfaces, Sidebar, States, Charts) plus which gradient surfaces belong to each group |
| Engine | `src/utils/theme-tokens.ts`, `theme-storage.ts`, `theme-gradients.ts` | merging preset tokens with overrides, `localStorage` persistence (with legacy migration) and the CSS gradient builders |
| Runtime | `src/contexts/theme-editor-context.tsx` + `src/hooks/use-theme-manager.ts` | the React state, and the low level writer of inline CSS variables |

`ThemeEditorProvider` is mounted in `App.tsx` above the router, so every page
(portal shell, auth pages, error pages) is themed – not only pages that render
`BaseLayout`.

**Presets.** `src/utils/estate-presets/` holds one file per built-in theme plus
`preset-factory.ts`, which fills in the tokens every theme shares. `index.ts`
orders the sixteen presets for the customizer and names `DEFAULT_ESTATE_THEME`
(`estate-navy`), applied to a visitor who has never chosen a theme. The picker
renders them as miniature interfaces in a searchable two column grid.
**Presets are flat**: no preset contains a gradient.

| Preset | Palette |
| --- | --- |
| Estate Navy | navy + gold (portal default) |
| Nairobi Slate | deep blue + earth gold |
| Emerald Estate | forest green + brass |
| Obsidian Gold | near-black + gold |
| Azure Property | product blue + teal |
| Indigo Estate | enterprise indigo + cyan |
| Terracotta Estate | warm architectural orange |
| Modern Graphite | neutral graphite + fresh green |
| Steel Blueprint | industrial steel + safety orange |
| Mocha Estate | mocha + clay earth tones |
| Burgundy Reserve | deep wine + brass |
| Arctic Mint | mint + cool slate |
| Oceanic | deep cyan + sky |
| Midnight Aurora | violet + cyan |
| Rose Quartz | rose + violet |
| Cyber Lime | acid lime on charcoal |

Each preset defines a light **and** a dark variant of every token the editor
exposes: background, card, popover, primary, secondary, muted, accent, border,
input, ring, the five chart colours, all eight sidebar tokens and the radius.

**Per-mode editing.** Colours are tuned per mode: the editor's Light/Dark switch
follows the app appearance but can be flipped to tune the other mode, and shows
the resolved value of the mode being edited. Edits are stored as *overrides*
(`overrides.light`, `overrides.dark` in `localStorage`), layered on top of the
selected preset, and are diffed against the preset so a value identical to the
preset is not stored. Applying another preset clears the overrides, and
"Portal default colours" drops the preset entirely to use `src/index.css`.

**Gradients are opt-in.** A fresh install is completely flat; gradients are
added from the editor and stored as overrides. `buildGradient(surface, variant)`
generates the blends (sheen, diagonal, aurora, mesh) from the surface's own
tokens via `color-mix()` and `var()`, so one gradient value blends correctly in
both modes – which is why the editor writes a gradient to **both** modes at once
instead of asking for it twice. A free text field accepts any custom CSS
gradient. `src/index.css` consumes them: `--background-gradient` on `body` and
the sidebar inset, `--sidebar-gradient` on the sidebar surfaces, and
`--primary-gradient` through the `.bg-brand-gradient` class used by the brand
panel, the sidebar mark and the customizer trigger.

**Semantic state colours** (`--success`, `--warning`, `--info`, and their
foregrounds) are editable like any other token but default to `src/index.css`,
because they carry meaning rather than branding.

**Surface polish.** `src/index.css` carries a small, theme aware depth layer so
components need no per-element classes: cards get a soft shadow mixed from
`--foreground`, clickable cards (property grid and list rows) lift on hover, the
inset panel reads as a raised surface, sidebar rows transition colour and nudge
towards the content, the active row grows an accent indicator bar (it uses
`--sidebar-ring`, so it is gold on Estate Navy), and page content eases in on
navigation. Every transform and animation is switched off under
`prefers-reduced-motion: reduce`.

Two small deviations from nppos: the storage key is portal-specific (nppos uses
`nppos:theme`), and the customizer is mounted *inside* `SidebarProvider` because
its Layout tab calls `useSidebar()`, which throws outside a provider. nppos also
keeps a second, partial theme persistence in `app-layout.tsx` that writes the
same key with fewer fields; that duplicate is intentionally not copied here.

## Property browsing and "My Properties"

Both the public browser (`/properties`) and the tenant view (`/my-properties`)
render the same presentation components from `src/components/properties/`:

| Component | Purpose |
| --- | --- |
| `PropertyCard` | grid card: cover image, status badge, title, specs, amenity tags |
| `PropertyRow` | compact list row: thumbnail, title, specs, meta |
| `PropertyMedia` | cover image with lazy loading and **initials placeholder** (e.g. "Pinnacle Tower - 1A" → `PT`) when a property has no image or the image fails to load |
| `LayoutToggle` | grid / list switcher |
| `PropertyStatusBadge` | availability (`Available`, `Occupied`, `Reserved`, `Under Maintenance`) and tenancy (`Active`, `Reserved`, `History`) badges |

Each page maps its own payload onto the shared `PropertyView`
(`toAvailablePropertyView`, `toTenantPropertyView`), so cards and rows are
defined once.

The chosen layout is remembered per page in `sessionStorage` through
`usePageState` (key `layout`), i.e. `/properties` and `/my-properties` keep
independent preferences.

The guest listing endpoint only selects descriptive fields — asset and purchase
information (`asset_category`, `purchase_date`, `net_purchase_amount`) is not
exposed publicly.

## Property details and related documents

`/properties/<unit>` renders the property details page, served by
`utility_billing.api.portal.property_details.get_property_details`.

| Viewer | Sees |
| --- | --- |
| Guest / any other user | details of **available** units only: gallery, description, amenities, specifications and a **Book Now** button (booking itself is a later phase) |
| Tenant of the unit (current or past allocation) | everything above **plus** the tenancy summary (contract, signed state, period), the account totals (invoiced / paid / outstanding) and every related document |
| Anybody else | `PermissionError` → the page shows "occupied or reserved, not linked to your account" |

Related documents are resolved for the caller's own Customers **and** the
requested property:

| Document | Reached through |
| --- | --- |
| Meter Reading | `Meter Reading.property` |
| Utility Service Request | `utility_property` header or `requested_properties` child rows |
| Sales Invoice | `Sales Invoice Item.meter_reading`, `Sales Invoice Meter Reading.meter_reading` or `utility_service_request` |
| Sales Order | `Sales Order Item.meter_reading`, `Sales Order Meter Reading.meter_reading` or `utility_service_request` |
| Payment Entry | `Payment Entry Reference` rows pointing at those invoices/orders |

`Sales Invoice` and `Sales Order` have no property field of their own, which is
why the meter reading and service request links are used. The queries live in
`api/portal/property_documents.py` (meter readings, service requests) and
`api/portal/property_vouchers.py` (orders, invoices, payments, totals).

## Frontend structure

```
rental-portal/src
├── contexts/portal-context.tsx   # portal role, linked customer, capabilities
├── contexts/user-context.tsx     # session user (from the Frappe boot) + logout
├── contexts/notification-context.tsx
├── lib/portal.ts                 # boot accessors and role/capability helpers
├── lib/doctype-map.ts            # doctype slug ↔ name mapping
├── lib/frappe-service.ts         # thin wrappers around frappe-react-sdk
├── types/portal.ts               # shared portal types
├── components/doctype/           # generic list/form UI built on standard APIs
├── components/fields/            # Frappe field renderers
├── components/properties/        # property card/row/media/layout switcher
├── components/command-search.tsx # command palette
├── components/theme-customizer/  # theme + sidebar layout customizer
└── app/                          # pages (auth, dashboard, properties, settings, doctype, ...)
```

## Tests

`utility_billing/utility_billing/tests/test_portal_roles.py` covers the role,
capability and allocation classification rules:

```bash
bench --site <site> run-tests --module utility_billing.utility_billing.tests.test_portal_roles
```
