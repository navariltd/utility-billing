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

## 🧱 Doctype Fields

| Field          | Type     | Description                                                     |
| -------------- | -------- | --------------------------------------------------------------- |
| `Fiscal Year`  | Link     | Required fiscal year                                            |
| `Start Date`   | Date     | Start date for billing                                          |
| `End Date`     | Date     | End date for billing                                            |
| `Cost Center`  | Link     | Optional cost center to track financials                        |
| `Project`      | Link     | Optional project association                                    |
| `Items`        | Table    | List of utility billing items and their amounts (child doctype) |
| `Total Amount` | Currency | Auto-calculated total of all listed item amounts                |

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

- Autofills all defined utility items into the request
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
