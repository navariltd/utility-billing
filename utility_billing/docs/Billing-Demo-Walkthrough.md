# Water billing demo walkthrough

This demo shows how a customer's monthly reading becomes a bill, including progressive rates, fixed charges and changes to the customer's billing arrangement.

## Before you start

Open [Desk](http://utility-billing.localhost:8000/desk) and use **Mwangaza Water Services**. All amounts below are in **KES**.

Complete the comparisons while the readings are drafts. Submit Amina's reading only near the end of the demo.

| Customer | Billing arrangement | Meter | Prepared reading | Starting total |
|---|---|---|---|---:|
| Amina Otieno | Water and sewerage | WM-1001 | MR-202611-00001 | 210 |
| James Mwangi | Water only | WM-1002 | MR-202611-00002 | 140 |
| Grace Wanjiku | Water plus a service charge | WM-1003 | MR-202611-00003 | 190 |
| Peter Kamau | Fixed monthly water and sewerage | Not needed | MR-202611-00004 | 700 |
| Faith Achieng | Water only in October; water and sewerage from November | WM-1004 | MR-202611-00005 | 75 |

The expected totals assume no earlier submitted readings for these meters. Amina, James and Grace start at **15 units**, with a previous reading of **0**. Faith starts at **5 units**.

## 1. Show how a structure describes the charges

1. Search for **Utility Bill Structure** and open **Residential Water and Sewerage**.
2. Show **Calculations and Charges**. The rows are read from top to bottom.
3. Point out the two row types:
   - **Calculation Only** works out part of a charge. It does not charge the customer directly.
   - **Billable Item** adds an actual Water or Sewerage line to the bill.
4. Show the three water calculations and the final Water item:

   | Row | What it calculates |
   |---|---|
   | Water: first 10 units | Up to 10 units at 10 each |
   | Water: next 10 units | The next 10 units at 8 each |
   | Water: above 20 units | Any remaining units at 6 each |
   | Water | Adds the three water amounts together |

5. Show the equivalent sewerage rows. Their rates are **5**, **4** and **3**.

**Explain:** “We work out each part of the consumption separately, then add the parts together. Only the final Water and Sewerage rows are charged. The separate Bands table is no longer needed for these structures.”

The abbreviations, such as **W1**, **W2** and **W3**, name the intermediate amounts. The final Water formula adds those names together. To change the pricing, create a new structure or amend an unused draft; an assigned, submitted structure should retain its agreed pricing history.

### Explain the if/else formulas

Read `amount if condition else another_amount` as: “Use this amount when the condition is true; otherwise use the other amount.”

| Water tier | Amount Formula | How to explain it |
|---|---|---|
| First 10 units | `consumption * 10 if consumption <= 10 else 10 * 10` | Charge all units if consumption is 10 or less; otherwise charge a full first tier of 100. |
| Next 10 units | `0 if consumption <= 10 else ((consumption - 10) * 8 if consumption <= 20 else 10 * 8)` | Charge nothing until consumption exceeds 10. Then charge the next units at 8, up to a full tier of 80. |
| Above 20 units | `(consumption - 20) * 6 if consumption > 20 else 0` | Charge only the units above 20, at 6 each. |

At 15 units, those three rows give **100**, **40**, and **0**. The final Water row adds them to **140**. Sewerage follows the same steps with its own rates.

## 2. Show the customer assignment and installed meter

1. Open **Utility Bill Structure Assignment** and filter Customer to **Amina Otieno**.
2. Open her assignment. It links her to **Residential Water and Sewerage** from **1 November 2026**.
3. Open **Warranty Claim**, filter Customer to Amina, and show the Closed installation record for **WM-1001**.

**What happens:** The assignment determines Amina's charges and when they apply. The meter installation record makes her meter available when recording consumption.

## 3. Record consumption and inspect the calculation

1. Open [Amina's prepared reading](http://utility-billing.localhost:8000/desk/meter-reading/MR-202611-00001).
2. Confirm Company **Mwangaza Water Services**, Customer **Amina Otieno**, Date **16 November 2026**, and meter **WM-1001**. Leave Property blank for these samples.
3. Show **Bill Structure Assignment**. It is selected automatically from the customer, company, property and reading date.
4. Enter **Current Reading = 15** and click **Save**. With a previous reading of 0, consumption is 15.
5. Expand **Calculation Details** to show each part:

   | Calculation | Amount |
   |---|---:|
   | First 10 units of water × 10 | 100 |
   | Remaining 5 units of water × 8 | 40 |
   | Water above 20 units | 0 |
   | **Water charge** | **140** |
   | First 10 units of sewerage × 5 | 50 |
   | Remaining 5 units of sewerage × 4 | 20 |
   | Sewerage above 20 units | 0 |
   | **Sewerage charge** | **70** |

6. Show **Rates**. It should contain only **Water** and **Sewerage**, totaling **210**.

**Explain:** “The breakdown explains the amount. It is not a second set of charges. We bill 140 plus 70, not the intermediate amounts again.”

The final Water line is one monthly charge of 140, and Sewerage is one monthly charge of 70. Consumption remains 15 units in the meter reading. Using one final charge keeps rounding from changing the tier totals.

## 4. Show the effect of different consumption

Stay on Amina's draft. Change Current Reading and save after each change.

| Current reading | Water | Sewerage | Total |
|---:|---:|---:|---:|
| 10 | 100 | 50 | **150** |
| 15 | 140 | 70 | **210** |
| 20 | 180 | 90 | **270** |
| 50 | 360 | 180 | **540** |

At 50 units, Water is **10 × 10 + 10 × 8 + 30 × 6 = 360**. The final tier continues for consumption above 20 units; it has no maximum in these sample formulas.

Restore Current Reading to **15** and save.

## 5. Compare other billing arrangements

### Water only

1. Open [James's reading](http://utility-billing.localhost:8000/desk/meter-reading/MR-202611-00002).
2. Confirm meter **WM-1002**, date **16 November 2026**, and Current Reading **15**. Save.

**Expected result:** Water is **140**, with no Sewerage line. James has a different structure, using the same progressive water calculation.

### Water plus a service charge

1. Open [Grace's reading](http://utility-billing.localhost:8000/desk/meter-reading/MR-202611-00003).
2. Confirm meter **WM-1003** and Current Reading **15**. Save.

**Expected result:** Water is **140**. The service charge is **50**, giving **190**.

3. Change Current Reading to **50** and save.

**Expected result:** Water becomes **360**. The service charge becomes **72**, giving **432**. This structure charges 20% of the final water amount, with a minimum service charge of 50. Its formula is `water_total * 0.2 if water_total * 0.2 >= 50 else 50`.

4. Restore Current Reading to **15** and save.

### Fixed monthly charges

1. Open [Peter's reading](http://utility-billing.localhost:8000/desk/meter-reading/MR-202611-00004).
2. Confirm Customer **Peter Kamau** and Date **16 November 2026**.
3. Leave the meter-reading Items table empty and save.

**Expected result:** Water is **500** and Sewerage is **200**, giving a fixed monthly bill of **700**. No consumption or meter is required. For now, a Fixed charge uses quantity 1 even if the item is marked as stock; the accounting treatment for that case is deferred.

### Optional: explain stock-item billing

The sample Water and Sewerage items are currently non-stock services. Their final bill lines therefore have quantity 1.

For Formula charges, when a billable item has **Maintain Stock** enabled, the same structure uses the tier quantities instead. The sample structures now contain the quantity formulas and source abbreviations needed for this.

For 15 units of stock Water, **Rates** and the Sales Order would show:

| Item | Quantity | Rate | Amount |
|---|---:|---:|---:|
| Water | 10 | 10 | 100 |
| Water | 5 | 8 | 40 |
| **Total water** | **15** | | **140** |

Show **Quantity Formula** on the calculation rows and **Stock Quantity Sources** (`W1, W2, W3`) on the final Water row. They tell the system which quantities belong to the Water total. For non-stock items, the quantities still explain the calculation but are combined into one final charge.

The site allows the same item on multiple sales lines. An actual stock movement happens when a Delivery Note or a Sales Invoice with Update Stock is submitted, rather than when the reading or Sales Order is submitted.

## 6. Show that the reading date selects the right structure

Do this before submitting any readings for Faith's meter.

1. Open [Faith's reading](http://utility-billing.localhost:8000/desk/meter-reading/MR-202611-00005).
2. Keep meter **WM-1004** and Current Reading **5**.
3. Change Date to **15 October 2026** and save.

**Expected result:** The old **Residential Water Only** assignment is selected. Water costs **50**, with no Sewerage charge.

4. Restore Date to **16 November 2026** and save.

**Expected result:** The current **Residential Water and Sewerage** assignment is selected. Water costs **50** and Sewerage **25**, totaling **75**.

5. Open her current assignment and follow **Previous Assignment**. The old record ends on **31 October**; the new one starts on **1 November**.

**Explain:** “We keep the customer's assignment history, so a past reading uses the pricing arrangement that applied at that time.”

## 7. Submit a reading and check the sales document

Do this after completing the comparisons.

1. Return to Amina's reading and confirm Date **16 November 2026**, Current Reading **15**, and total **210**.
2. Click **Submit** and confirm.
3. Open **Sales Order**, filter Customer to Amina, and open the newly created Draft order.

**Expected result:** There are exactly two charge lines: Water **140** and Sewerage **70**. The total before any additional taxes is **210**. Calculation-only rows do not appear as order items.

**Explain:** “Submitting the reading creates the sales document for the final charges. It does not record a payment.”

### Optional: show duplicate-month protection

Create another reading for Amina dated **17 November 2026**, using the same company, meter, price list and warehouse. Enter Current Reading **20** and save. Her previous submitted reading is now 15, so new consumption is 5.

Try to submit it. Submission should be blocked because this assignment has already been billed for November. No second Sales Order should be created. Leave this extra reading unsubmitted.

## 8. Change a customer's future billing arrangement

This step changes James's billing from December onward.

1. Open James's submitted **Bill Structure Assignment**.
2. Click **Change Bill Structure**, choose **Residential Water and Sewerage**, and enter Effective Date **1 December 2026**.
3. Click **Create Assignment**.

**Expected result:** A new assignment starts on 1 December. The old assignment ends on 30 November, and the new record links to it through **Previous Assignment**.

4. Open James's draft reading, change its date to **1 December 2026**, keep Current Reading **15**, and save.

**Expected result:** With no earlier submitted readings for James, the new assignment gives Water **140** and Sewerage **70**, totaling **210**.

5. Restore the reading date to **16 November 2026** and save.

**Expected result:** The original water-only assignment is selected again, and the total returns to **140**. The new December assignment stays in place for future billing.

## If a result differs

- **No assignment:** Check the date, customer, company and property. These samples use Mwangaza Water Services and a blank Property.
- **Different consumption:** Check Previous Reading. Submitted readings affect what counts as new consumption.
- **No meter:** Check that the customer's meter installation record is Closed. Peter does not need one.
- **A past reading is refused:** A later reading may already have been submitted for the meter. Complete the date comparisons while the readings are still drafts.
- **A formula reports an unknown name:** Check the abbreviation and row order. A row can use results from earlier rows.
- **Old fields are still showing:** Hard-refresh and reopen the form.
