# ⛽ Meter Reading Doctype

The **Meter Reading** doctype is a core component of the [Utility Billing](https://github.com/navariltd/utility-billing) app for ERPNext. It allows service providers to efficiently track and bill customers based on utility consumption such as water, electricity, or gas.

It captures utility usage for a given customer and automatically generates a **Sales Order** based on the usage and applicable tariffs. This reduces manual data entry and automates billing.

![Meter Reading Screenshot](https://raw.githubusercontent.com/navariltd/utility-billing/refs/heads/develop/utility_billing/docs/images/meter-reading.png)

## 📋 Workflow

```mermaid
graph TD
    A[Service Request] --> B{Meter Reading}
    B --> C[Sales Order]
    C --> D[Sales Invoice]
    D --> E[Payment]
```

## ✅ Steps to Use

1. **Select Customer**
2. **Add Utility Item(s)** and enter the **Current Reading**
3. System calculates usage (Current - Previous Reading)
4. On **Submit**, the system auto-generates a **Sales Order**

## 🧱 Doctype Structure

| Field                                 | Type                       | Description                                     |
| ------------------------------------- | -------------------------- | ----------------------------------------------- |
| `Customer`                            | Link                       | Linked to Customer master                       |
| `Date`                                | Date                       | Date of meter reading                           |
| `Property`                            | Link                       | Auto-fetched from customer                      |
| `Currency` / `Price List`             | Link                       | Billing currency and applicable price list      |
| `Items`                               | Table (Meter Reading Item) | Enter previous and current readings per utility |
| `Rates`                               | Table (Read-Only)          | Auto-fetched tariff rates for preview           |
| `Company` / `Cost Center` / `Project` | Link                       | Accounting and cost tracking fields             |

---

## 📦 Related Child Doctypes

- **Meter Reading Item**
  Captures individual utility item readings.

  - `Utility Item` (e.g., Water, Electricity)
  - `Previous Reading`
  - `Current Reading`
  - `Usage` (auto-calculated)

- **Meter Reading Tariff Rate**
  Linked to tariff configurations that determine the charge per unit used.

## ⚙️ Automation on Submit

When a **Meter Reading** is submitted:

- Usage is calculated per item.
- Tariffs are applied to compute billable amounts.
- A **Sales Order** is automatically created.

## 🚀 Quick Navigation

[![Home](https://img.shields.io/badge/Home-DEF4FF?style=for-the-badge&logo=github&logoColor=000)](https://github.com/navariltd/utility-billing)
[![Full Documentation](https://img.shields.io/badge/Full_Documentation-6366F1?style=for-the-badge&logo=readthedocs&logoColor=fff)](https://github.com/navariltd/utility-billing/wiki)
[![ERPNext Docs](https://img.shields.io/badge/ERPNext_Docs-FF6B6B?style=for-the-badge&logo=erpnext&logoColor=fff)](https://docs.erpnext.com)
[![Frappe Framework](https://img.shields.io/badge/Frappe_Framework-00C49A?style=for-the-badge&logo=frappe&logoColor=fff)](https://frappeframework.com/docs)
[![Community Forum](https://img.shields.io/badge/Community_Forum-F59E0B?style=for-the-badge&logo=discourse&logoColor=fff)](https://discuss.frappe.io)
[![Report Issue](https://img.shields.io/badge/Report_Issue-E63946?style=for-the-badge&logo=githubissues&logoColor=fff)](https://github.com/navariltd/utility-billing/issues)
[![Website](https://img.shields.io/badge/Website-1E293B?style=for-the-badge&logo=googlechrome&logoColor=fff)](https://navari.co.ke)
