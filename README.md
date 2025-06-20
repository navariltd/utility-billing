<!-- Utility Billing & Property Management -->

# 💡 Utility Billing & Property Management for ERPNext

The **Utility Billing & Property Management App** is a powerful addition to [ERPNext](https://erpnext.com), designed to streamline **utility billing**, **property leasing**, and **tenant management**. Ideal for municipal utilities, real estate managers, and property developers.

![Overview](./utility_billing/docs/images/workspace.png)

## 🔌 [Utility Billing](./utility_billing/docs/Utility-Billing.md)

A comprehensive module for managing utility services (water, electricity, gas, etc.) with end-to-end billing automation.

#### **Core Features**

1. **🔧 Configurable Billing**

   - Customizable tariffs, price lists, and customer grouping (residential/commercial)
   - Auto-generated sales orders/invoices (draft or submitted)

2. **📟 Meter & Service Management**

   - Track consumption via **meter readings**
   - **Service requests** workflow: Survey → BOM → Billing
   - Meter numbers as serial numbers

3. **⚡ Bulk Operations**

   - **Mass billing** for multiple customers
   - Merge sales orders per customer

4. **🔄 Automated Workflows**
   - Customer creation from service requests
   - Flow: Meter Reading → Sales Order → Invoice → Payment

#### **Key Integrations**

- **CRM**: Leads → Customers
- **Inventory**: Meters as serials
- **Accounting**: Auto-invoicing

[![Explore More](https://img.shields.io/badge/%F0%9F%91%89%20Explore%20More-6f42c1?style=for-the-badge&logo=github)](./utility_billing/docs/Utility-Billing.md)

## 🏢 [Property Management](./utility_billing/docs/Property-Management.md)

The **ERPNext Property Management** module simplifies rental operations from tenant onboarding to recurring rent and utility billing.

### 🌟 **Key Features:**

- 🏘️ **Property Structure**: Organize by Project → Building → Floor → Unit
- 📝 **Service Requests**: Capture tenant interest & unit selection
- 📄 **Contracts**: Define rental terms, durations, and escalation rules
- 👥 **Tenant**: Managed as a customer for seamless billing integration
- 💰 **Deposits & Booking**: Generate sales orders for upfront payments
- 📃 **Invoicing**: Automate rent billing via **Auto Repeat**
- ⚡ **Utility Billing**: Bill utility usage per unit and contract
- 🔄 **Full Workflow Support**: From inquiry to billing with smooth transitions
- 📈 **Escalation Rules**: Support periodic rent increases

### ✅ **Benefits:**

- Seamless management of units, leases, and tenants
- Recurring and utility billing under a single customer record
- Built-in support for renewals, notices, and changes

## [![Explore More](https://img.shields.io/badge/%F0%9F%91%89%20Explore%20More-6f42c1?style=for-the-badge&logo=github)](./utility_billing/docs/Property-Management.md)

## 🧾 Key Doctypes & Customizations

Explore the doctypes that power the system. Below are categorized lists of **new doctypes** and **customizations**.

### ✨ Customized Doctypes

- 📑 [Contract](./utility_billing/docs/Contract.md)
- 🧾 [Sales Order and Sales Invoice](./utility_billing/docs/Sales-Order-and-Invoice)
- 📦 [Item](./utility_billing/docs/Utility-Billing.md#-3-important-notes.md)
- 💲 [Item Price](./utility_billing/docs/Utility-Billing.md#-13-price-lists--tariffs)

### 🆕 New Doctypes

- ⚙️ [Utility Billing Settings](./utility_billing/docs/Settings.md)
- 🏢 [Utility Property](./utility_billing/docs/Property.md)
- 📝 [Utility Service Request](./utility_billing/docs/Service-Request.md)
- 🧾 [Utility Bill Structure](./utility_billing/docs/Bill-Structure.md)
- 📈 [Meter Reading](./utility_billing/docs/Meter-Reading.md)
- 🪙 [Billing Adjustment Rule](./utility_billing/docs/Billing-Adjustment-Rule.md)

## 📊 Reports

Get actionable insights from your utility and property data with our built-in reports. These reports help you monitor availability, manage service requests, oversee tenancy details, and track utility consumption—empowering better decision-making across your operations.

### Main Reports:

- **🏢 Property Availability Report** – Track real-time inventory, occupancy, and asset value.
- **🛠️ Service Request Summary** – Monitor service request lifecycles and billing progress.
- **📝 Tenancy Summary Report** – Manage leases, durations, and contract changes.
- **🔌 Meter Reading Summary** – Analyze utility consumption, tariff blocks, and billing.

## [![View Reports](https://img.shields.io/badge/%F0%9F%91%89%20Explore%20More-6f42c1?style=for-the-badge&logo=github)](./utility_billing/docs/Reports.md)

## ⚙️ Demo Data Management

For testing and demonstration purposes, the Utility Billing & Property Management app provides a convenient way to generate and clear demo data. This allows you to quickly populate your system with sample records to explore functionalities without affecting your live data.

[![Explore More](https://img.shields.io/badge/%F0%9F%91%89%20Explore%20More-6f42c1?style=for-the-badge&logo=github)](./utility_billing/docs/Demo-Data.md)

## 🛠️ Installation (Self-Hosted)

```bash
# Install Frappe Bench
https://github.com/frappe/bench

# Install ERPNext
https://github.com/frappe/erpnext

```

Clone this app into your apps folder and run:

```bash
bench get-app utility_billing https://github.com/navariltd/utility-billing.git
bench --site [site_name] install-app utility_billing
```

## 📚 Documentation & Support

Need help? Browse detailed guides, FAQs, or open an issue in our GitHub repo.

[![Full Documentation](https://img.shields.io/badge/Full_Documentation-6366F1?style=for-the-badge&logo=readthedocs&logoColor=fff)](https://github.com/navariltd/utility-billing/wiki)
[![ERPNext Docs](https://img.shields.io/badge/ERPNext_Docs-FF6B6B?style=for-the-badge&logo=erpnext&logoColor=fff)](https://docs.erpnext.com)
[![Frappe Framework](https://img.shields.io/badge/Frappe_Framework-00C49A?style=for-the-badge&logo=frappe&logoColor=fff)](https://frappeframework.com/docs)
[![Community Forum](https://img.shields.io/badge/Community_Forum-F59E0B?style=for-the-badge&logo=discourse&logoColor=fff)](https://discuss.frappe.io)
[![Report Issue](https://img.shields.io/badge/Report_Issue-E63946?style=for-the-badge&logo=githubissues&logoColor=fff)](https://github.com/navariltd/utility-billing/issues)
[![Website](https://img.shields.io/badge/Website-1E293B?style=for-the-badge&logo=googlechrome&logoColor=fff)](https://navari.co.ke)
