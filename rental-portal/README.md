# Rental Portal

The tenant-facing single page application of **Utility Billing & Property
Management**. It is built with React 19, TypeScript, Vite and
`frappe-react-sdk`, and is served by Frappe at `/utility-billing`.

## Features

| Area | What the tenant can do |
| --- | --- |
| Properties | Browse available units as a guest or tenant; inspect gallery, amenities, specs, location and availability |
| Booking | Book an available unit, choose lease dates, track, extend, modify or cancel a booking |
| My Properties | See active, reserved and historical tenancies with account totals |
| Billing | Review submitted Sales Invoices and Sales Orders, open an invoice and pay through the configured gateway |
| Support | Raise a ticket from a property or booking, read the timeline and reply |
| Notifications | Unread badge and notification feed; preferences through the standard Frappe page |
| Account | Profile and password flows through standard Frappe user pages |
| Admin | `/users` for System Managers/Administrators and generic `/app/:doctype` browsing |
| Appearance | Light/dark mode, estate colour presets, gradients and sidebar layout customiser |

The backend scopes every document to the session user's linked Customers; the
browser never decides who owns a property, invoice or ticket.

## Routes

| Route | Access | Page |
| --- | --- | --- |
| `/auth/sign-in` | Guest | Session login |
| `/auth/sign-up` | Guest, when enabled | Website User sign-up |
| `/auth/forgot-password` | Guest | Frappe password reset |
| `/properties` | Public | Available property grid/list |
| `/properties/:property` | Public / tenant | Property gallery, details and related documents |
| `/properties/:property/book` | Signed in | Booking form |
| `/dashboard` | Signed in | Tenant overview |
| `/my-properties` | Signed in | Current and historical allocations |
| `/bookings` | Signed in | Current/history bookings and actions |
| `/invoices` | Signed in | Invoices, orders and payment action |
| `/settings/notifications` | Signed in | Notification feed |
| `/users` | System Manager / Administrator | User administration |
| `/app/:doctype/:id` | Permission based | Generic Frappe list/form UI |

## Project layout

```
src/
├── app/                    # route pages (auth, dashboard, properties, bookings, invoices, support)
├── components/
│   ├── properties/         # shared cards, rows, media, status badges
│   ├── payments/           # payment dialog and gateway redirect
│   ├── support/            # support list, create form, detail, reply, timeline
│   ├── doctype/ + fields/  # generic metadata-driven list/form renderers
│   ├── theme-customizer/   # presets, colours, gradients and layout
│   └── ui/                 # shadcn/Radix primitives
├── config/routes.tsx       # route tree used by the router and command search
├── contexts/               # session, portal role, notifications
├── lib/                    # Frappe call helpers, doctype slugs, formatting
└── types/                  # shared portal payload types
```

## Local development

```bash
cd apps/utility_billing/rental-portal
yarn install
yarn dev
```

The Vite dev server proxies Frappe API calls to the bench, so sign in with a
site user while developing. Use `yarn lint` for Oxlint and
`npx tsc -p tsconfig.app.json --noEmit` for type checking.

## Production build

```bash
cd apps/utility_billing/rental-portal
yarn build
```

The build:

1. writes hashed assets to `utility_billing/public/utility-billing/`;
2. copies the generated `index.html` to
   `utility_billing/www/utility-billing.html`, which the
   `utility_billing/www/utility-billing.py` controller serves with the Frappe
   session boot embedded.

Commit the regenerated portal HTML/assets with front-end changes.

## Backend endpoints

| Endpoint | Purpose |
| --- | --- |
| `utility_billing.api.portal.context.get_portal_context` | Session user, portal role and capabilities |
| `utility_billing.api.properties.get_available_properties` | Public property listing |
| `utility_billing.api.portal.properties.get_my_properties` | Tenant allocations |
| `utility_billing.api.portal.property_details.get_property_details` | Property details, tenancy and related documents |
| `utility_billing.api.portal.bookings.get_booking_options` | Booking defaults and pending request |
| `utility_billing.api.portal.bookings.create_booking` | Create a draft booking request |
| `utility_billing.api.portal.bookings.get_my_bookings` | Current and historical bookings |
| `utility_billing.api.portal.bookings.modify_booking` / `extend_booking` / `cancel_booking` | Booking lifecycle actions |
| `utility_billing.api.portal.payments.get_customer_documents` | Payable invoices and order advances |
| `utility_billing.api.portal.payments.initiate_payment` | Gateway checkout URL |
| `utility_billing.api.portal.support.*` | Property/booking support tickets and replies |
| Standard Frappe endpoints | Login, sign-up, password reset, profile, notifications, files and generic doctype CRUD |

## Demo accounts

Generate demo data from **Utility Billing Settings → Generate Demo Data** and
sign in with any account from
[`13-Demo-Data.md`](../utility_billing/docs/13-Demo-Data.md).

All demo accounts use the password `Demo@12345`. They are Website Users linked
to CRM Customers and are intended for demos/training only.

## More documentation

- [Customer portal guide](../utility_billing/docs/12-Customer-Portal.md)
- [Demo dataset and billing approaches](../utility_billing/docs/13-Demo-Data.md)
- [Property management](../utility_billing/docs/03-Property-Management.md)
- [Billing adjustment rules](../utility_billing/docs/07-Billing-Adjustment-Rules.md)
- [Rent billing by Item Price](../utility_billing/docs/08-Rent-Billing.md)
