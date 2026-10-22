# 🧾 Rent Billing by Item Price

Rent for a leased property can be billed in two ways, selected per site in
**Utility Billing Settings → Rent Billing Approach**:

| Approach | How rent is billed |
| --- | --- |
| **Auto Repeat** | The reference Sales Order/Invoice is copied on schedule. Increments are applied when a document's Auto Repeat completes. |
| **Item Price** | The scheduled document is billed at the rate valid on the billing date. Rates come from dated **Item Price** records generated from the lease. |

With the **Item Price** approach no Auto Repeat documents are created, so a
single recurring document picks up the new rate automatically when it becomes
valid.

---

## 1. Property Service Item

Every billable property owns a **service item** used as its rent line, so rent
can be traced back to the property without extra lookups.

- The item is a non-stock, non-asset sales item named **exactly like the
  property name**.
- It is created automatically when **Auto Create Property Service Item** is
  enabled in Utility Billing Settings (`1` by default).
- The **Service Item Group** setting controls the item group, falling back to
  the property category and then to `Utility and Rental`.
- When an item with the property name already exists it is **linked**, not
  duplicated.
- Group properties (`is_group = 1`) never get a service item.
- Saving a Utility Service Request also ensures every requested property has
  its service item.

Run `bench --site <site> migrate` to backfill service items for existing
properties through the `create_property_service_items` patch.

---

## 2. Defining Item Prices

On a submitted **Utility Service Request**, use **Define → Item Prices** to
open the schedule modal.

### Modal fields

| Field | Purpose |
| --- | --- |
| **Property** | The property being priced. Limited to properties requested on this service request. |
| **Starting Rate** | Rent for the first period of the selected property. |
| **Customer** | Restricts the prices to a customer. Leave blank for prices that apply to all customers. |
| **Lease Start / Lease End** | The lease period. The end date drives how many periods are generated. |
| **Price List** | Price list the Item Prices are created in. Needed to create prices; the schedule can be previewed without it. |
| **Billing Adjustment Rule** | Optional. Fills the increment fields below. |
| **Frequency** | How often rent is billed (Monthly, Quarterly, Yearly, ...). |
| **Every (Months)** | Months between increments, for example `12` for yearly. |
| **Increase By (%)** | Percentage added at every increment, for example `5`. |
| **Based On** | **Original Amount** grows linearly; **Last Adjusted Amount** compounds. |
| **Start After (Months)** | Grace period before the first increment applies. |
| **Replace Existing Prices** | Deletes prices previously generated for the same item and customer before creating new ones. |
| **Rates** | The schedule of the selected property. **From**, **To** and **Rate** are all editable, rows can be added and deleted, and the values are kept as the final schedule. |

### Editing the schedule by hand

The **Rates** table is not just a preview: any value in it can be changed. A
period can be re-dated, re-priced, split in two, extended or removed, and new
periods can be added. As soon as the table is touched the schedule is treated as
**manual**:

- The hand edited rows are the final schedule: a preview never overwrites them,
  and they are **not validated while you are still editing**.
- Only a change to a **main** field (property, starting rate, lease dates,
  frequency, adjustment rule, increment interval/percentage/basis) discards the
  manual rows and generates a fresh schedule.
- Switching properties keeps each property's manual rows, so nothing is lost
  when moving between properties.
- Coverage of the contract period is checked when you click **Create Item
  Prices**; the prices are written only when the schedule covers it. Creating
  prices writes the manual rows exactly as shown.

Whatever the source, a schedule must **cover the whole contract period** of the
property: it has to start with the contract, run without gaps or overlaps and
reach the contract end. A manual schedule that falls short is rejected on
**Create Item Prices** with a message naming the problem, and nothing is
written. The contract period is taken from the property's row in **Requested
Properties**, falling back to the document's **Contract Start/End Date**.

Hand editing is only offered when **Rent Billing Approach** is **Item Price**.

### Price list resolution

The modal uses the document's **Price List** when one is set. If the request has
none, the price list is resolved in this order:

1. the customer's `default_price_list`;
2. the **Default Price List** configured in Utility Billing Settings.

A price list you choose yourself is never overwritten. The schedule can be
previewed without a price list; one is only required when creating prices.

Selecting a **Billing Adjustment Rule** copies its frequency, interval, percentage,
effective-after and basis into the modal. Every field then stays editable, so a
single lease can be tuned without changing the shared rule.

### Pricing one property at a time

The **Rent Schedule** section works on a single property at a time:

1. Pick the **Property**. The list only offers properties requested on this
   service request.
2. Enter its **Starting Rate**. The rate is remembered per property.
3. The schedule fills in automatically in the **Rates** table and is
   recalculated whenever the lease dates, frequency, increment settings or
   starting rate change. A summary above the table shows the period count,
   date range and first/last rate. The **Price List** is only needed when
   creating prices, so the schedule previews without it.
4. Any value in the **Rates** table can be changed by hand: re-date a period,
   re-price it, add a row or delete one. The rows become the final schedule and
   are only regenerated when a main field changes. See
   [Editing the schedule by hand](#editing-the-schedule-by-hand).
5. Use **Create Item Prices** to write the Item Prices for that property.

After a property is created, the modal automatically moves to the next
property that still needs prices and closes once every property has been
done. Switching properties manually never loses a starting rate or a manual
edit.

Use **Preview** to expand the periods and check the rates before saving.

### How rates are calculated

1. Periods run from the lease start date, one period per billing frequency
   until the end date is reached (or the safety limit, for open-ended leases).
2. The first period uses the **Starting Rate** entered in the modal.
3. An increment applies once `Effective After (Months) + Increment Interval` has
   elapsed, and then repeats every `Increment Interval`.
4. The **Adjustment Basis** decides how each increment is applied:
   - **Original Amount** adds the percentage of the starting rate, so the rate
     grows linearly.
   - **Last Adjusted Amount** adds the percentage of the previous period's rate,
     so the rate compounds. There is no upper limit; the compounded rate follows
     the percentage for the whole lease.
5. A **Manual Rate** starting on the first day of a period replaces the
   generated rate from that period onwards and becomes the new base for
   subsequent increments.
6. **Consecutive periods sharing a rate are merged into one.** Billing periods
   exist so a rate can change on a known date, but a single `Item Price` is
   enough to describe a stretch where the rate never changes. A 5-year monthly
   lease with a yearly increment therefore produces **6 `Item Price` records**
   covering a year each, not 60 monthly records.

For a 5-year lease starting at 100,000 per month with a 5% annual increment:

| Period | Original Amount | Last Adjusted Amount |
| --- | --- | --- |
| 2026-01-01 → 2026-12-31 | 100,000 | 100,000 |
| 2027-01-01 → 2027-12-31 | 105,000 | 105,000 |
| 2028-01-01 → 2028-12-31 | 110,000 | 110,250 |
| 2029-01-01 → 2029-12-31 | 115,000 | 115,762.50 |
| 2030-01-01 → 2030-12-31 | 120,000 | 121,550.63 |

If no increment is configured, a single rate covers the whole lease and **one**
`Item Price` is created.

### Generated records

- One **`Item Price`** per stretch of unchanged rate, per property and customer,
  carrying `valid_from` and `valid_upto` for that stretch.
- These are **ordinary Item Prices** — no custom fields are added to the
  DocType. The property is expressed by the item itself, because each property
  owns a service item named after it.
- Each record is linked to:
  - **Item Code** — the property's service item
  - **Customer** — the tenant, when one is selected
- Re-running the action is safe: periods that already have an overlapping
  `Item Price` are skipped and reported as `skipped`.
- **Replace Existing Prices** deletes by item, price list and customer. Because
  a property's prices are always scoped to its own service item, prices of
  other properties and items are never affected.

### Viewing and correcting what was created

The **Item Price Schedule** section of the Utility Service Request shows an
**Item Price Summary** HTML field. It looks up each property's service item,
reads the Item Prices for those items, and renders them grouped by property
showing each period's dates, customer and rate. Properties with no prices yet
are listed as such. This is a view of the actual `Item Price` records, not a
separate copy, so it can never drift from what billing will use.

The summary is an **editor**. For each property you can:

- change a period's **From** and **To** dates;
- change its **rate**;
- **remove** a period with the ✕ button;
- **add** a new period with **Add period**.

Changed rows are highlighted and a count of pending changes appears next to the
**Save Schedule** button, which stays disabled until something actually differs.
Clicking it asks for confirmation and writes the whole schedule of every edited
property at once.

What the save does and does not do:

- Existing periods have their dates and rate updated, removed periods are
  deleted, and added periods are inserted as new `Item Price` records.
- Before anything is written, each property's schedule is validated as a whole:
  it must start with the contract, run without gaps or overlaps and reach the
  contract end. A schedule that does not cover the contract is rejected with a
  message and **nothing is written**, so a partial edit cannot leave a stretch
  of the contract unpriced.
- Every submitted record is re-checked on the server against the request's own
  properties; a record belonging to another item is skipped and reported rather
  than written. An edit can never reach an unrelated `Item Price`, even if its
  name is submitted deliberately.
- The outcome is reported as periods added, updated, removed or skipped, so a
  partial result is always visible rather than silent.
- Saving is only available when **Rent Billing Approach** is **Item Price**.

### Generated records

- One **Item Price** per property, per period, scoped to the service item, the
  price list and (optionally) the customer.
- Each generated row is marked **Is Rent Schedule**, so only generated prices
  are removed by *Replace Existing Generated Prices*; manually maintained
  prices are never deleted.
- The full schedule is written to the read-only **Item Price Schedule** table
  on the Utility Service Request for reference.
- Re-running the action is safe: periods that already have an overlapping Item
  Price are skipped and reported as `skipped`.

---

## 3. Extension Points

| Module | Responsibility |
| --- | --- |
| `utils/item_price_schedule.py` | Pure schedule maths (no database access). |
| `utils/item_price_periods.py` | Merging consecutive periods that share a rate. |
| `utils/item_prices.py` | Rate period persistence, increment rule resolution and duplicate detection. |
| `utils/item_price_validation.py` | Coverage rules of a hand edited schedule (no database access). |
| `utils/item_price_schedule_helpers.py` | Payload parsing, options building and line construction. |
| `utils/item_price_actions.py` | Whitelisted preview and create actions of the modal. |
| `utils/item_price_scope.py` | Which records of a request may be written to. |
| `utils/item_price_summary.py` | Reading created Item Prices back and grouping them by property. |
| `utils/item_price_summary_html.py` | Rendering the editable Item Price Summary field. |
| `utils/item_price_summary_actions.py` | Whitelisted save action of the Item Price Summary editor. |
| `utils/item_price_uom.py` | UOM resolution validated against the items being priced. |
| `utils/service_item.py` | Property service item creation and resolution. |
