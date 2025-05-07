## ⚙️ Utility Billing Settings

The **Utility Billing Settings** Doctype centralizes critical configuration options to control how utility billing behaves in ERPNext, specifically around automation, customer creation, sales flows, and penalty management.
![Utility Settings Screenshot](https://raw.githubusercontent.com/navariltd/utility-billing/refs/heads/develop/utility_billing/docs/images/utility-settings.png)

### 📦 Sales & Stock Settings

| **Field**                                                        | **Description**                                                                                                                         |
| ---------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| **Sales Order Creation State**                                   | Determines whether Sales Orders are created in `Draft` or `Submitted` state upon generation from utility workflows.                     |
| **Stock Entry Creation State**                                   | Sets the default submission state (`Draft` or `Submitted`) for Stock Entries. Useful when tracking inventory with utilities.            |
| **Create single invoice for multiple sales orders per customer** | When enabled, consolidates multiple Sales Orders for the same customer into a single Sales Invoice.                                     |
| **Sales Invoice Creation State**                                 | Specifies if new Sales Invoices are automatically created as `Draft` or `Submitted`.                                                    |
| **Sales Invoice Grace Period (in days)**                         | Defines the number of days after invoice posting before the due date. It affects the calculation of overdue invoices and penalty logic. |

---

### 📝 Service Request Settings

| **Field**                                                  | **Description**                                                                                                        |
| ---------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| **Create Customer from Utility Service Request on Submit** | Automatically creates a Customer when a Utility Service Request is submitted, simplifying onboarding.                  |
| **Enable Extra Rows for SO/SI Creation**                   | Allows additional table rows for complex service plans during Sales Order or Invoice creation.                         |
| **Require Contract Before SO/SI/Customer Creation**        | Prevents Sales Orders, Invoices, or Customer creation without a valid linked contract. Ensures contractual compliance. |

---

### 💸 Penalty Settings

Penalties are used to encourage timely payment and enforce billing discipline.

| **Field**                         | **Description**                                                                                            |
| --------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| **Apply Penalty**                 | Master switch to activate penalty rules on overdue invoices.                                               |
| **Penalty Type**                  | Determines the type of penalty: `Percentage` of overdue amount or a `Fixed Amount`.                        |
| **Penalty Value**                 | Numeric value of the penalty. A percentage (e.g., `2`) or amount (e.g., `500`) based on the selected type. |
| **Penalty Grace Period (days)**   | Grace period after the due date before penalty is applied.                                                 |
| **Recurring Penalty**             | When enabled, the penalty will reapply periodically (e.g., weekly) after the grace period.                 |
| **Recurrence Interval (in days)** | Interval in days for recurring penalty application (e.g., `7` for weekly).                                 |
| **Max Penalty Cap**               | Maximum amount that penalties can accumulate to per invoice to prevent overcharging.                       |

---

### 🔁 Auto Repeat Settings (Hidden)

| **Field**                                          | **Description**                                                                                                                                     |
| -------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Sales Invoice Auto Repeat Frequency** _(Hidden)_ | Defines auto-generation frequency for recurring invoices. Options include `Daily`, `Weekly`, `Monthly`, etc. Used by background jobs if configured. |

## 🚀 Quick Navigation

[![Home](https://img.shields.io/badge/Home-DEF4FF?style=for-the-badge&logo=github&logoColor=000)](https://github.com/navariltd/utility-billing)
[![Full Documentation](https://img.shields.io/badge/Full_Documentation-6366F1?style=for-the-badge&logo=readthedocs&logoColor=fff)](https://github.com/navariltd/utility-billing/wiki)
[![ERPNext Docs](https://img.shields.io/badge/ERPNext_Docs-FF6B6B?style=for-the-badge&logo=erpnext&logoColor=fff)](https://docs.erpnext.com)
[![Frappe Framework](https://img.shields.io/badge/Frappe_Framework-00C49A?style=for-the-badge&logo=frappe&logoColor=fff)](https://frappeframework.com/docs)
[![Community Forum](https://img.shields.io/badge/Community_Forum-F59E0B?style=for-the-badge&logo=discourse&logoColor=fff)](https://discuss.frappe.io)
[![Report Issue](https://img.shields.io/badge/Report_Issue-E63946?style=for-the-badge&logo=githubissues&logoColor=fff)](https://github.com/navariltd/utility-billing/issues)
[![Website](https://img.shields.io/badge/Website-1E293B?style=for-the-badge&logo=googlechrome&logoColor=fff)](https://navari.co.ke)
