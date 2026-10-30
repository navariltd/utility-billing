# Demo Data

Demo data builds a complete, explorable company — buildings, tenants, contracts,
rent schedules, meter readings, invoices and support tickets — so you can try
every screen before entering live records, or train staff on realistic data.

> Use it on development and staging sites only. Demo accounts share one published
> password and the images are external links.

## What gets created

| Area                | Demo data                                                                                   |
| ------------------- | ------------------------------------------------------------------------------------------- |
| Customers           | 12 residential and commercial customers                                                     |
| Portal user         | One website user linked to a customer                                                       |
| Properties          | 6 buildings/estates and 26 lettable units                                                   |
| Images              | A cover image and gallery for every property                                                |
| Service requests    | 15 requests — 12 signed tenancies and 3 unsigned reservations                               |
| Contracts           | One submitted contract per request, signed where the request is                             |
| Rent pricing        | Item Price schedules or Auto Repeat, following your rent setting                            |
| Utility pricing     | Water, electricity and sewer prices with tiered blocks for residential and commercial lists |
| Meter readings      | 13 submitted readings that raise meter orders                                               |
| Orders and invoices | Rent orders, meter orders and a first rent invoice per leased unit                          |
| Support tickets     | 12 tickets with replies, including resolved examples                                        |
| Adjustment rules    | Three examples: fixed, linear and compounding                                               |

Everything is created in a separate **Utility and Rental (Demo)** company, so it
never mixes with your real vouchers. Dates are relative to the day you generate
the data, and names, sizes and rents are fixed, so reports and screens stay
consistent.

## The properties in the demo

- **The Pinnacle Towers - Kilimani** — studios, one and two-bedroom units, and a
  penthouse
- **Kileleshwa Heights Apartments** — bedsitters to three-bedroom units
- **Greenpark Estate - Runda** — townhouses and a maisonette
- **Westlands Business Plaza** — office suites and a retail shop
- **Mombasa Beachfront Villas** — beachfront villas
- **Ruiru Garden Court** — garden apartments

Each has a cover image and gallery, so the portal looks populated. Images are
remote, so no files are uploaded to your site.

## The sample tenant login

One demo customer has a portal login and owns the largest slice of the data —
four service requests, four support tickets and three meter readings — so every
portal page has something to show.

**Email:** `wanjiku.kamau@demo.utilitybilling.test`
**Password:** `Demo@12345`

Sign in at `/utility-billing`. The other demo customers exist only in the desk, so
unrelated tenants never share a login.

## Generate it

1. **From Settings** — open **Utility Billing Settings** and click **Generate
   Demo Data**.

   ![Generate Demo Data — Settings](./images/demo-settings.png)

2. **From the command line** (System Manager only):

   ```bash
   bench --site <site> execute utility_billing.setup.demo.setup_demo_data
   ```

Generating twice is safe: existing master records, leases, readings and tickets
are skipped rather than duplicated.

### How rent and utilities are priced in the demo

- The demo follows the **Rent Billing Approach** already set on your site; it
  never changes it.
- With **Item Price**, each leased unit gets a dated schedule built from its lease
  dates and adjustment rule, and available units get an open-ended rent price so
  the portal booking page can show a rent.
- With **Auto Repeat**, each leased unit gets a first invoice with an Auto Repeat
  attached, so the schedule has a document to run from.
- Water, electricity and sewer prices are created for both the residential and
  the commercial price list, with tiered blocks, so reading a meter produces a
  proper block breakdown.
- The Pinnacle Tower water meter, MTR10001, carries several months of readings
  chained from a previous reading of 0, so history appears in the portal.

> Payment gateway accounts are **not** created. To try online payment, configure
> a gateway for the demo company first.

## Clear it

Use **Clear Demo Data** in Utility Billing Settings or the toolbar, or run:

```bash
bench --site <site> execute utility_billing.setup.demo.clear_demo_data
```

Clearing removes the demo company with all its vouchers and ledger entries, then
the meter readings, contracts, service requests, bill structures, tickets,
generated prices and property items, the demo users and their customer links, and
finally the demo master data. Records in other companies are untouched. If a step
cannot be completed it is reported so you can clean it up by hand.

## Good to know

- **Isolation** — everything sits under the demo company.
- **Documents are drafts by default** — with the default creation states, rent
  orders and invoices stay drafts and the portal shows nothing. Set the states to
  _Submitted_ in [Settings](./01-Settings.md) before generating if you want the
  billing pages populated.
- **Images need internet** — the portal shows a placeholder when an image cannot
  be loaded.
- **Clean up before reusing a site** — clear the demo before removing the app or
  handing the site to real users.
- Every portal page touched by this data is described in
  [Customer Portal](./12-Customer-Portal.md).

---
