# Customer Portal

The Rental Billing customer portal is a React single page application served at
`/utility-billing` and built from the `rental-portal` folder of this app.

## Feature map

| Feature | Frontend | Backend |
| --- | --- | --- |
| Public property browser | `/properties`, `PropertyCard`, `PropertyRow` | `api.properties.get_available_properties` |
| Property details and gallery | `/properties/:property` | `api.portal.property_details.get_property_details` |
| Unit booking | `/properties/:property/book` | `api.portal.bookings.*` |
| My bookings | `/bookings` | `api.portal.bookings.*` |
| My properties / tenancy | `/my-properties` | `api.portal.properties.get_my_properties` |
| Invoices, orders and payments | `/invoices` | `api.portal.payments.*` |
| Meter readings | `/meter-readings`, `/meter-readings/:reading` | `api.portal.meter_readings.*` |
| Support tickets and replies | property and booking support dialogs | `api.portal.support.*` |
| Notifications | `/settings/notifications` | standard Frappe notification log |
| Profile and password | `/app/user/<user>` | standard Frappe user pages |
| Admin user list | `/users` | standard User APIs |
| Generic doctype list/form | `/app/:doctype(/:id)` | standard Frappe metadata and CRUD |

## Authentication

| Flow | Implementation |
| --- | --- |
| Sign in | `frappe-react-sdk` `useFrappeAuth` (Frappe session login) |
| Sign up | `frappe.core.doctype.user.user.sign_up` (creates a Website User and emails a verification link) |
| Forgot password | `frappe.core.doctype.user.user.reset_password` |
| Change password | `frappe.core.doctype.user.user.update_password` |
| Logout | Frappe session logout |

The portal never stores or transmits passwords itself; credential handling is
delegated to Frappe. Sign-up is available only when
`Website Settings → Disable Signup` is unchecked.

`utility_billing/www/utility-billing.py` embeds the standard Frappe session boot
so the SPA receives `frappe.boot` and the session user without an extra call.

## Portal roles and capabilities

`utility_billing.api.portal.context.get_portal_context` resolves the portal role
and the capabilities used by navigation and guards:

* `Guest` – anonymous visitor; may browse properties.
* `Tenant` – a user with the `Customer` or `Tenant` role linked through
  `Customer.portal_users`.
* `Property Owner` / `Landlord`, `Property Manager`, `Utility Customer` – role
  based, reserved for their dashboards.

Guests receive `browse_properties` only. Authenticated portal roles currently
receive the full capability map (`browse_properties`, `view_dashboard`,
`view_my_units`, `manage_profile`, `manage_notifications`).

## Tenant linkage and access control

A tenant's records resolve through standard ERPNext documents:

```
User (Customer.portal_users) → Customer → Contract (party_type = Customer)
  → Contract Utility Property Item → Utility Property
```

`get_my_properties` classifies allocations as:

| State | Rule |
| --- | --- |
| `Reserved` | active allocation on a Contract that is not signed |
| `Active` | active, signed allocation that has not ended |
| `History` | inactive allocation or an ended lease |

Property details, invoices, orders, payments, meter readings and support
tickets are always scoped to the caller's own Customers **and** the requested
property/document. Client-supplied ownership, amounts and statuses are never
trusted.

## Bookings

A portal booking is a draft `Utility Service Request` created for the caller's
Customer. It carries the property row, lease dates and tenant notes.

- The unit stays publicly available until staff submit the request.
- A second pending booking for the same unit is rejected; the tenant is sent to
  the existing request.
- Tenants can modify dates, extend or cancel a pending/current booking according
  to the same ownership rules.
- Submitting the request creates the Contract; signing it moves the unit from
  `Reserved` to `Active`.

The portal booking form reads defaults from
`get_booking_options`: property, monthly rent, deposit, lease dates and any
pending booking.

## Invoices, orders and payments

`/invoices` lists every submitted, payable Sales Invoice and Sales Order of the
signed-in Customer.

- An invoice is paid for its outstanding amount.
- A Sales Order is paid as an advance for its unbilled balance.
- The portal asks the selected gateway controller for a checkout URL and
  redirects the customer. It does **not** create Payment Entries or Payment
  Requests itself; the gateway records the payment on the reference document.
- A `Payment Gateway Account` must exist for the document's company. The demo
  data does not create one.

## Meter readings

`/meter-readings` lists every non-cancelled `Meter Reading` recorded for the
signed-in Customer, newest first, one row per reading:

- the reading's date and name, the unit (unit number, house number or plot
  number of the `Utility Property`) and the meters of each line;
- total consumption (the stored consumption of each line, falling back to
  `current_reading - previous_reading`) and the amount billed for the reading;
- draft/submitted state, plus totals for the returned page (readings,
  consumption, amount and latest date).

Selecting a row opens `/meter-readings/:reading`, which shows the full reading:

- reading number, date, unit, customer, company, price list and status;
- every meter line with its previous reading, current reading, consumption and
  amount;
- the block distribution: each `Utility Tariff Block` billed, with the quantity,
  rate and amount, and the total amount of the reading.

Rows are scoped to the caller's Customers (`Customer.portal_users`); a cancelled
reading is never listed and a reading of another Customer answers with a
`DoesNotExistError`. The demo dataset chains several monthly readings on one
meter (MTR10001, starting from a previous reading of 0) so the list and the
block distribution have something to show.

## Support tickets

Customers raise standard ERPNext `Issue` documents from:

- **a booking** (`create_support_issue`), or
- **an active/reserved property** (`create_property_support_issue`).

Each ticket stores `utility_property`, `utility_service_request` (when known),
the Customer, the company and `via_customer_portal`. Replies are Comments on the
Issue and are rendered with the document timeline. Status counts (open, replied,
resolved) come from the Issue status.

## Property details and related documents

| Viewer | Sees |
| --- | --- |
| Guest / unrelated user | details of **available** units only |
| Tenant of the unit (current or past) | details plus tenancy summary, account totals and related documents |
| Anybody else | `PermissionError` → "occupied or reserved, not linked to your account" |

Related documents are resolved through:

| Document | Reached through |
| --- | --- |
| Meter Reading | `Meter Reading.property` |
| Utility Service Request | header `utility_property` or `requested_properties` rows |
| Sales Invoice | `Sales Invoice Item.meter_reading`, `Sales Invoice Meter Reading.meter_reading` or `utility_service_request` |
| Sales Order | `Sales Order Item.meter_reading`, `Sales Order Meter Reading.meter_reading` or `utility_service_request` |
| Payment Entry | `Payment Entry Reference` rows pointing at those invoices/orders |

## API surface

| Endpoint | Guest | Purpose |
| --- | --- | --- |
| `utility_billing.api.portal.context.get_portal_context` | yes | session/role/capability bootstrap |
| `utility_billing.api.properties.get_available_properties` | yes | public property browser |
| `utility_billing.api.portal.property_details.get_property_details` | yes | property details; own tenancy/documents when applicable |
| `utility_billing.api.portal.properties.get_my_properties` | no | tenant allocations |
| `utility_billing.api.portal.bookings.get_booking_options` | no | booking defaults and pending booking |
| `utility_billing.api.portal.bookings.create_booking` | no | create a draft booking |
| `utility_billing.api.portal.bookings.get_my_bookings` | no | current/history bookings |
| `utility_billing.api.portal.bookings.modify_booking` | no | change pending/current booking dates |
| `utility_billing.api.portal.bookings.extend_booking` | no | extend a booking |
| `utility_billing.api.portal.bookings.cancel_booking` | no | cancel a booking |
| `utility_billing.api.portal.support.get_property_support` | no | tickets for a property |
| `utility_billing.api.portal.support.get_booking_support` | no | tickets for a booking |
| `utility_billing.api.portal.support.get_support_issue` | no | one ticket and timeline |
| `utility_billing.api.portal.support.create_support_issue` | no | raise from a booking |
| `utility_billing.api.portal.support.create_property_support_issue` | no | raise from a property |
| `utility_billing.api.portal.support.reply_to_support_issue` | no | customer reply |
| `utility_billing.api.portal.payments.get_payment_gateways` | no | configured gateway accounts |
| `utility_billing.api.portal.payments.get_customer_documents` | no | invoices, orders and totals |
| `utility_billing.api.portal.payments.initiate_payment` | no | gateway checkout URL |
| `utility_billing.api.portal.meter_readings.get_customer_meter_readings` | no | meter readings, consumption and amounts |
| `utility_billing.api.portal.meter_readings.get_customer_meter_reading` | no | one reading with its block distribution |

## Generic doctype browsing (`/app` routes)

The portal reuses metadata-driven `DocTypeList` / `DocTypeForm` components for
`/app/:doctype(/:id)` pages. They use standard Frappe endpoints:

- `frappe.desk.form.load.getdoctype`
- `frappe.desk.reportview.get` and `get_count`
- `frappe.desk.form.load.getdoc`
- `frappe.client.save` / `frappe.desk.form.save.savedocs`
- `frappe.desk.search.search_link`
- `frappe.model.workflow.*`

Slug mapping lives in `src/lib/doctype-map.ts`. Users without permission are
redirected by `PermissionGuard` to the forbidden page.

## Notifications and appearance

- Notification feed and unread badge use the standard notification log.
- Preferences are handled by `/app/notification-settings/<user>`.
- The theme customiser supports light/dark mode, 16 estate presets, per-mode
  token overrides, opt-in gradients, radius, sidebar variant and layout.
- Theme selections persist in `localStorage` under `rental-portal:theme`.

## Frontend structure

```
rental-portal/src
├── app/                          # auth, dashboard, properties, bookings, invoices, meter readings, support pages
├── components/
│   ├── properties/               # card, row, media, status and layout components
│   ├── payments/                 # pay button and gateway dialog
│   ├── support/                  # support list/create/detail/reply/timeline
│   ├── doctype/ + fields/        # generic Frappe metadata renderers
│   ├── theme-customizer/         # presets, colours, gradients, layout
│   └── ui/                       # shared primitives
├── config/routes.tsx             # route tree and command-search metadata
├── contexts/                     # user, portal role, notifications
├── lib/                          # Frappe helpers, doctype slugs, formatting
└── types/                        # shared payloads
```

## Demo accounts

The demo generator creates 12 Website Users linked to Customers. See
[Demo Data](./Demo-Data.md) for every email. All demo accounts use the password
`Demo@12345`; use them for staging and training only.

## Tests

`utility_billing/utility_billing/tests/test_portal_roles.py` covers role,
capability and allocation classification rules:

```bash
bench --site <site> run-tests --module utility_billing.utility_billing.tests.test_portal_roles
```
