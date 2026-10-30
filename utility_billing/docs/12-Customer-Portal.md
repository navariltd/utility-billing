# Customer Portal

The customer portal is the tenant's side of the system, served at
`/utility-billing`: browse available units, book one, follow the tenancy, see
invoices and meter readings, pay online and talk to support.

## What a tenant can do

| Page                     | What it is for                                                                               |
| ------------------------ | -------------------------------------------------------------------------------------------- |
| **Properties**           | Browse every available unit, even before signing in                                          |
| **Property details**     | Photos, amenities, size, availability and — for the tenant — their own tenancy and documents |
| **Book a unit**          | Reserve a unit and send the request to the office                                            |
| **My Bookings**          | Pending and past bookings; change dates, extend or cancel                                    |
| **My Properties**        | Current and past tenancies, grouped as _Reserved_, _Active_ and history                      |
| **Invoices**             | Every bill: amount, due date, items, meter readings, taxes and what is still owed            |
| **Orders**               | Deposits and other orders, with the advance paid and the balance                             |
| **Meter Readings**       | Each reading with consumption and how the tariff blocks were applied                         |
| **Support**              | Raise a ticket from a booking or a property and follow the replies                           |
| **Notifications**        | Alerts from the office                                                                       |
| **Profile / Appearance** | Name, password, and the portal's theme                                                       |

## Signing in

- **Sign in** uses the user's Frappe account, created when the office links them
  to a customer.
- **Sign up** is offered only when the site allows it
  (**Website Settings → Disable Signup** unchecked), and sends a verification
  email.
- **Forgot password** sends a reset link; the password is never handled by the
  portal itself.

Staff prepare a tenant by giving the customer's **Portal Users** table a user
account with the **Customer** role. Without that link the tenant signs in but
sees no property, invoice or reading.

## Browsing and booking

- A guest sees only **available** units. A tenant of a unit also sees that unit's
  tenancy summary and related documents; anyone else is told the unit is
  occupied or reserved.
- **Book a unit** creates a draft request for the signed-in customer with the
  unit, the lease dates and any notes. The office reviews and submits it, then
  the contract is created.
- A unit can only have one pending booking — a second attempt sends the tenant to
  the booking they already made.
- Tenants can change the dates, extend or cancel a pending or current booking.
  Signing the contract moves the unit from _Reserved_ to _Active_.

## Invoices, orders and payments

The list shows every bill with its date, due date, status and amount. Opening one
shows:

- the amount still due, with its due state — _due in N days_, _due today_ or
  _overdue_;
- the net total, taxes, grand total and the amount already paid;
- tabs for the items, the meter readings behind the utility lines (each linking
  to the reading) and the taxes;
- a summary panel with the full breakdown.

**Pay** is available from the list and from the document. An invoice is paid for
its outstanding amount; an order is paid as an advance for the unbilled balance.
Payment happens on the gateway's checkout page and is recorded against the
document, so the portal never stores card details.

> Online payment needs a **Payment Gateway Account** for the company of the
> document. Without one, the Pay button has nothing to send the tenant to.

## Meter readings

The reading list shows the date, the unit, the meters and the total consumption
and amount, newest first. Opening a reading shows each meter with its previous
and current reading, the consumption, and the tariff blocks the consumption was
split into — the same breakdown the bill was built from.

Only the tenant's own readings are visible; cancelled readings never appear.

## Support tickets

Tenants raise a ticket from a booking or from an active or reserved property, and
the conversation is shown as a timeline on the ticket. Status counts (open,
replied, resolved) come from the ticket's state, so the office answers in the
same place it always does.

## Notifications and appearance

- The bell shows unread notifications, with preferences on the notification
  settings page.
- The theme customiser offers light and dark mode, estate colour presets, an
  optional gradient background, corner radius and sidebar layout. Choices are
  remembered in the browser.

## If something does not work

- **A tenant sees an empty portal** — the user is not linked in the customer's
  **Portal Users** table, or the documents are still drafts. See
  [Settings](./01-Settings.md).
- **No Pay button** — no payment gateway account exists for that company.
- **A booking cannot be made** — the unit is no longer available, or the tenant
  already has a pending booking for it.
- **A document is not listed** — it is a draft or cancelled; only submitted,
  payable documents are shown.

---
