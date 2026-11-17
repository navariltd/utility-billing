# 🧾 Utility Bill Structure

The **Utility Bill Structure** doctype is a configurable template used within the [Utility Billing](https://github.com/navariltd/utility-billing) app for ERPNext. It allows users to predefine billable utility items and related charges, which can then be reused and auto-filled in **Utility Service Requests**.

This reduces repetitive data entry and ensures billing consistency across similar requests for utilities such as water, electricity, or gas.

![Utility Bill Structure Screenshot](https://raw.githubusercontent.com/navariltd/utility-billing/refs/heads/develop/utility_billing/docs/images/utility-bill-structure.png)

---

## 📋 Purpose

The Utility Bill Structure acts as a **template** for recurring utility billing formats. When a service provider initiates a **Utility Service Request**, this structure can be linked to automatically populate the necessary items, their amounts, and associated metadata like cost center and project.

---

## ✅ How to Use

1. Create a **Utility Bill Structure** with predefined utility items, amounts, and optional discounts.
2. Link this structure to a **Utility Service Request**.
3. Upon linking, all items and charges are auto-filled in the request.

---

## Calculate monthly bills

For monthly customer billing, use **Calculations and Charges** and a submitted **Bill Structure Assignment**. The reading date selects the assignment that applies to the customer.

- **Calculation Only** rows work out intermediate amounts. Give each one a Description and an Abbreviation so later rows can use its result. These rows do not require an Item and do not become charges.
- **Billable Item** rows produce the actual charges. Choose an Item, then a fixed amount or an Amount Formula.

Rows calculate from top to bottom. For example, at 15 units:

| Description | Abbreviation | Amount Formula | Row Type |
|---|---|---|---|
| First 10 units | W1 | `consumption * 10 if consumption <= 10 else 10 * 10` | Calculation Only |
| Next 10 units | W2 | `0 if consumption <= 10 else ((consumption - 10) * 8 if consumption <= 20 else 10 * 8)` | Calculation Only |
| Above 20 units | W3 | `(consumption - 20) * 6 if consumption > 20 else 0` | Calculation Only |
| Water | WATER | `W1 + W2 + W3` | Billable Item |

Read each formula as “use this amount if the condition is true; otherwise use the amount after else.” The Water charge is **140**. Intermediate values of 100, 40 and 0 appear under **Calculation Details** on Meter Reading, while **Rates** contains only the final billable Water line.

**Fixed** charges always use quantity 1 and the fixed amount, including stock items. Their stock accounting treatment is deferred.

For **Formula** charges, the system checks **Maintain Stock** on the billable Item:

- **Non-stock items:** one final charge with quantity 1. This avoids rounding a combined total into an average unit rate.
- **Stock items:** actual quantities are billed. For progressive pricing, give each calculation row a **Quantity Formula**, then list its abbreviations in the final item's **Stock Quantity Sources**.

For the Water example, use `consumption if consumption <= 10 else 10` for W1's quantity, `0 if consumption <= 10 else (consumption - 10 if consumption <= 20 else 10)` for W2, and `consumption - 20 if consumption > 20 else 0` for W3. Set the Water billable row's Stock Quantity Sources to `W1, W2, W3`. At 15 units, a stock item produces two Water lines: 10 at 10 and 5 at 8. The unused third tier produces no charge line. The same configuration produces one Water charge of 140 when the Item is non-stock.

Stock source amounts must add up to the billable amount. For the consumption item, their quantities must also add up to the meter consumption. A formula-based stock item without tier sources needs its own Quantity Formula; missing quantities are rejected rather than defaulting to 1.

Enable **Allow Item to Be Added Multiple Times in a Transaction** in Selling Settings for stock tier lines. Sales Orders do not move stock; submit a Delivery Note or a Sales Invoice with Update Stock to record the actual stock movement. Configure the quantity formulas in the units used for the billed stock item.

The sample structures use formulas instead of a separate Bands table. Older band-based structures remain supported for compatibility. **Total Fixed Charges** excludes calculation-only rows and does not predict formula charges before a reading is entered.

When copying a structure into a Utility Service Request, calculation-only rows are excluded. Consumption formulas are evaluated through Meter Reading.

See the [demo walkthrough](Billing-Demo-Walkthrough.md) for examples with meters, sewerage, fixed monthly charges and assignment history.

---

## 🧱 Doctype Fields

| Field          | Type     | Description                                                     |
| -------------- | -------- | --------------------------------------------------------------- |
| `Fiscal Year`  | Link     | Required fiscal year                                            |
| `Start Date`   | Date     | Start date for billing                                          |
| `End Date`     | Date     | End date for billing                                            |
| `Cost Center`  | Link     | Optional cost center to track financials                        |
| `Project`      | Link     | Optional project association                                    |
| `Items`        | Table    | Billable items and intermediate calculation rows |
| `Total Amount` | Currency | Total fixed billable charges; excludes intermediate calculations                |

---

## 📦 Child Doctype: Utility Bill Structure Item

Each item in the bill structure is defined in this child table.

| Field      | Type     | Description                                            |
| ---------- | -------- | ------------------------------------------------------ |
| `Item`     | Link     | Reference to the billable item (e.g., Water, Sewerage) |
| `Amount`   | Currency | Amount to be charged                                   |
| `Discount` | Float    | Optional discount in percentage (%)                    |
| `Total`    | Currency | Net total after applying discount (auto-calculated)    |

---

## ⚙️ Automation Features

When used within a **Utility Service Request**, the Utility Bill Structure:

- Autofills billable utility items into the request
- Calculates totals and applies discounts
- Enables standardized billing and streamlined sales workflows

---

## 🚀 Quick Navigation

[![Home](https://img.shields.io/badge/Home-DEF4FF?style=for-the-badge&logo=github&logoColor=000)](https://github.com/navariltd/utility-billing)
[![Full Documentation](https://img.shields.io/badge/Full_Documentation-6366F1?style=for-the-badge&logo=readthedocs&logoColor=fff)](https://github.com/navariltd/utility-billing/wiki)
[![ERPNext Docs](https://img.shields.io/badge/ERPNext_Docs-FF6B6B?style=for-the-badge&logo=erpnext&logoColor=fff)](https://docs.erpnext.com)
[![Frappe Framework](https://img.shields.io/badge/Frappe_Framework-00C49A?style=for-the-badge&logo=frappe&logoColor=fff)](https://frappeframework.com/docs)
[![Community Forum](https://img.shields.io/badge/Community_Forum-F59E0B?style=for-the-badge&logo=discourse&logoColor=fff)](https://discuss.frappe.io)
[![Report Issue](https://img.shields.io/badge/Report_Issue-E63946?style=for-the-badge&logo=githubissues&logoColor=fff)](https://github.com/navariltd/utility-billing/issues)
[![Website](https://img.shields.io/badge/Website-1E293B?style=for-the-badge&logo=googlechrome&logoColor=fff)](https://navari.co.ke)
