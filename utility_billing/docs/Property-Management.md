# II. 🏢 **Property Management**

---

## 🧱 Overview

The **Property Management Module** in ERPNext provides a structured, end-to-end solution for managing rental properties — from onboarding tenants to recurring rent invoicing and utility billing.

It supports:

- 🏠 Property structuring (Project → Building → Unit)
- 📝 Service Requests to capture tenant intent
- 💰 Deposit collection
- 📄 Contract generation
- 🔁 Rent invoicing via Auto Repeat
- ⚡ Utility billing

![Utility & Property Overview](./images/uility_property.png)

---

## 🏗️ Property Hierarchy

Properties are structured as:

```bash
Real Estate Project
 ├── Building A
 │    ├── Floor 1
 │    │    └── Unit 101
 │    ├── Floor 2
 │    │    └── Unit 201
 └── Building B
      └── Unit 301
```

Each unit is independently managed for contracts, billing, and utilities.

---

## 🔄 Workflow: From Service Request to Billing

### 🔌 **Utility Service Request Process**

> 💡 **Contract is optional but required based on _Utility Billing Settings_.**  
> 🧠 **Customer can be automatically created on submit**, depending on configuration in settings.

```mermaid
graph TD
    A["Customer / Lead / Prospect (CRM)"] --> B["Create Service Request"]
    B --> C["Auto Create Customer on Submit (if enabled)"]
    C --> F["Contract"]
    C --> E["Create Sales Order (Deposit) - Optional/Required via Settings"]
    E --> F
    F --> G
    C --> G["Create Sales Invoice (Rent)"]
    E --> G
    G --> H["Auto Repeat (Recurring Invoicing)"]
```

## 📂 Step-by-Step Functional Process

### 1️⃣ Utility Service Request (Initiation)

![Service Request Details Tab](./images/service_request_details_tab.png)  
![Service Request Lease Tab](./images/service_request_lease_tab.png)

Start by creating a **Utility Service Request**, which captures:

- 🧍 Tenant details (customer)
- 🏢 Desired unit(s)
- 📅 Contract dates and terms
- 💼 Lease duration

This acts as the **lead intake form** for tenants and is the **trigger point** for the rental flow.

---

### 2️⃣ Generate Sales Order (Deposit / Booking)

![Sales Order Modal](./images/service_request_salesorder_modal.png)

Directly from the service request:

- Create a **Sales Order** for:
  - 💰 Security deposit
  - 📌 Booking/advance payments
- Amounts auto-pulled from service request
- Tracks payment before lease start

---

### 3️⃣ Create Property Contract

![Contract Screenshot](./images/contract.png)

From an approved Service Request:

- Draft a **Property Contract**
- Define:
  - Contract period
  - Deposit terms
- Link:
  - Tenant (Customer)
  - Unit(s)

This contract manages the tenency.

---

### 4️⃣ Sales Invoice (Recurring Rent)

![Sales Invoice Modal](./images/service_request_salesinvoice_modal.png)

Rent is billed based on the contract:

- 💼 Auto Repeat can auto-generate invoices
- Supports:
  - Monthly / Quarterly / Annual cycles
  - Rent escalation by %

---

### 5️⃣ Auto Repeat & Escalation

- 🔁 **Recurring Billing**: Set by contract

- 🪙 **[Billing Adjustment Rule](./Billing-Adjustment-Rule.md)**
  Defines **all escalation logic**, including:

  - Recurrence frequency (e.g., monthly, quarterly)
  - Penalty and surcharge conditions
  - Custom increase rates
  - Escalation intervals
  - Manual override permissions
    Applied **per property** to control billing behavior and adjustments comprehensively.

---

## 💎 Strategic Benefits

✅ Captures tenant interest via **Utility Service Request**  
✅ Smooth transition to **Contracts**, **Sales Orders**, and **Invoices**  
✅ Centralized control of units, leases, and utilities  
✅ Seamless **rent + utility billing** under one customer  
✅ Enables workflows like **vacation notice**, **contract renewal**, or **meter change**

---

## 🚀 Quick Navigation

[![Home](https://img.shields.io/badge/Home-DEF4FF?style=for-the-badge&logo=github&logoColor=000)](https://github.com/navariltd/utility-billing)
[![Full Documentation](https://img.shields.io/badge/Full_Documentation-6366F1?style=for-the-badge&logo=readthedocs&logoColor=fff)](https://github.com/navariltd/utility-billing/wiki)
[![ERPNext Docs](https://img.shields.io/badge/ERPNext_Docs-FF6B6B?style=for-the-badge&logo=erpnext&logoColor=fff)](https://docs.erpnext.com)
[![Frappe Framework](https://img.shields.io/badge/Frappe_Framework-00C49A?style=for-the-badge&logo=frappe&logoColor=fff)](https://frappeframework.com/docs)
[![Community Forum](https://img.shields.io/badge/Community_Forum-F59E0B?style=for-the-badge&logo=discourse&logoColor=fff)](https://discuss.frappe.io)
[![Report Issue](https://img.shields.io/badge/Report_Issue-E63946?style=for-the-badge&logo=githubissues&logoColor=fff)](https://github.com/navariltd/utility-billing/issues)
[![Website](https://img.shields.io/badge/Website-1E293B?style=for-the-badge&logo=googlechrome&logoColor=fff)](https://navari.co.ke)
