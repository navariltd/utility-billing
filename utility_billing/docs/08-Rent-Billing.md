# Rent Billing

Rent can repeat in two ways. Choose one per site in **Utility Billing Settings →
Rent Billing Approach**:

| Approach        | How rent is billed                                                                                 | Best when                                                                                 |
| --------------- | -------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| **Auto Repeat** | A reference invoice or order is copied on schedule; increments are applied when a repeat completes | You want standard ERPNext Auto Repeat documents and a simple setup                        |
| **Item Price**  | The recurring document is billed at the rate valid on the billing date, from a dated rent schedule | Rents change over the lease and one recurring document should pick up new rates by itself |

This guide covers the **Item Price** approach in detail; Auto Repeat users only
need the first section.

## The property rent item

Every billable unit has a **service item** used as its rent line, named exactly
like the property.

- It is non-stock and not an asset — it only carries the rent rate.
- It is created automatically while **Auto Create Property Service Item** is on
  in [Settings](./01-Settings.md).
- The **Service Item Group** setting decides the item group.
- If an item with the property's name already exists it is reused, never
  duplicated.
- Group properties (buildings) never get a rent item.

The item is filled on the property record as **Service Item**. You rarely need to
touch it; you do need it when reading the rent schedule, because every rent price
belongs to the property's item.

## Generate the rent for a lease

1. Open the submitted [Utility Service Request](./04-Service-Requests.md) of the
   lease.
2. Choose **Define → Item Prices**.
3. Pick the **Property** — only units requested on that request are offered.
4. Enter the **Starting Rate** for the first period.
5. Set the lease period and the billing **Frequency**; optionally pick a
   [Billing Adjustment Rule](./07-Billing-Adjustment-Rules.md) to pre-fill the
   increase settings.
6. Press **Preview** to expand the periods and check the rates.
7. Choose **Create Item Prices**. The modal moves on to the next unit that still
   needs prices and closes when all units are done.

### What each field does

| Field                       | Purpose                                                                                  |
| --------------------------- | ---------------------------------------------------------------------------------------- |
| **Property**                | The unit being priced                                                                    |
| **Starting Rate**           | Rent for the first period; remembered per unit                                           |
| **Customer**                | Limits the prices to one tenant; leave empty to price for all                            |
| **Lease Start / Lease End** | The period that drives how many periods are generated                                    |
| **Price List**              | The list the Item Prices are created in; needed to create, not to preview                |
| **Billing Adjustment Rule** | Optional; fills the increment fields below                                               |
| **Frequency**               | How often rent is billed — Monthly, Quarterly, Yearly …                                  |
| **Every (Months)**          | Months between increases, e.g. `12` for yearly                                           |
| **Increase By (%)**         | Percentage added at each increase, e.g. `5`                                              |
| **Based On**                | **Original Amount** grows in a straight line; **Last Adjusted Amount** compounds         |
| **Start After (Months)**    | Wait before the first increase applies                                                   |
| **Replace Existing Prices** | Removes prices generated earlier for the same item and customer before creating new ones |
| **Rates**                   | The actual schedule — every row is editable                                              |

### How the rates are calculated

1. Periods run from the lease start, one per billing frequency, until the lease
   ends.
2. The first period uses the **Starting Rate**.
3. An increase applies after _Start After (Months) + Every (Months)_ and then
   repeats at each interval.
4. _Original Amount_ adds the percentage of the starting rate; _Last Adjusted
   Amount_ adds the percentage of the previous rate.
5. A **Manual Rate** starting on the first day of a period replaces the rate from
   that period on, and becomes the base for later increases.
6. **Periods that share a rate are merged.** A five-year monthly lease with a
   yearly increase produces six Item Prices covering a year each, not sixty
   monthly ones.

For 100,000 per month with a 5% annual increase over five years:

| Period | Original Amount | Last Adjusted Amount |
| ------ | --------------- | -------------------- |
| 2026   | 100,000         | 100,000              |
| 2027   | 105,000         | 105,000              |
| 2028   | 110,000         | 110,250              |
| 2029   | 115,000         | 115,762.50           |
| 2030   | 120,000         | 121,550.63           |

With no increase configured, one rate covers the whole lease and one Item Price
is created.

## Adjusting the schedule by hand

The **Rates** table is an editor, not just a preview. You can re-date a period,
change its rate, split it, extend it, delete it or add a new one.

- Once you edit a row, that table becomes your schedule: a preview will not
  overwrite it, and it is not validated until you create the prices.
- Changing a main field — property, starting rate, lease dates, frequency,
  adjustment rule or the increment settings — discards the manual rows and
  generates a fresh schedule.
- Switching between units keeps each unit's manual rows and starting rate.
- The schedule must **cover the whole lease** of that unit: start on the contract
  first day, have no gaps or overlaps, and reach the contract end. A schedule
  that falls short is refused with a message and nothing is written. The lease
  period comes from the unit's row in **Requested Properties**, falling back to
  the request's contract dates.

## Checking and correcting what was created

The **Item Price Summary** on the service request lists every unit with its
periods, dates, customer and rate — read straight from the Item Prices that
billing will use, so it cannot go out of date. Units without prices are shown as
such.

The summary is also an editor:

- change a period's **From**, **To** or rate;
- remove a period with the ✕ button;
- add a period with **Add period**.

Changed rows are highlighted and a count of pending changes appears next to
**Save Schedule**, which stays disabled until something differs. **Save Schedule**
writes every edited unit at once, after confirming. Before writing it checks that
each unit's schedule still covers the contract; if it does not, nothing is saved,
so part of a lease can never be left unpriced.

> Saving from the summary is only available with the **Item Price** approach.

## What gets created

- One **Item Price** per stretch of unchanged rate, per unit, in the chosen price
  list and, when given, for that customer.
- These are ordinary ERPNext Item Prices — the unit is identified by its service
  item.
- Re-running **Create Item Prices** is safe: periods that already have an
  overlapping price are skipped and reported.
- **Replace Existing Prices** only removes the prices generated for the same
  item, price list and customer; manually maintained prices are untouched.

## If something does not work

- **"Schedule does not cover the contract"** — a period was deleted or re-dated
  and leaves a gap. Re-preview the unit, or add the missing period in the summary
  editor.
- **A rate did not change on the expected date** — an increase only applies after
  _Start After (Months) + Every (Months)_. Check both values, or add a manual
  period starting on the review date.
- **The rent item is missing** — enable **Auto Create Property Service Item** and
  save the property again.
- **Nothing was created** — no **Price List** was chosen; previewing works
  without one, creating does not.

---
