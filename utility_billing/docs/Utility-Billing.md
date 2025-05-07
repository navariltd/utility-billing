# I. 🔌 **Utility Billing Overview**

### 🧩 Main Functionalities

- 💬 Service Request Management
- 📏 Meter Reading
- 💰 Tariff Management
- 🧾 Bulk Billing (Mass Billing)

## 🔍 Key Modules & Features

### 🧾 1. **Utility Billing Setup**

#### 🛠️ 1.1 Utility Billing Settings

Configure preferences in the **Utility Settings** doctype.

**Key Fields:**

- 🔄 **Sales Order / Invoice / Stock Entry Creation State** — Choose between "Draft" or "Submitted"
- 📦 **Merge Sales Orders** — One invoice per customer across multiple orders

![Utility Settings Screenshot](https://raw.githubusercontent.com/navariltd/utility-billing/refs/heads/develop/utility_billing/docs/images/utility-settings.png)

[![👉 Explore Utility Billing Settings](https://img.shields.io/badge/👉_Explore_Utility_Billing_Settings-6f42c1?style=for-the-badge&logo=readthedocs&logoColor=fff)](./Settings.md)

#### 👥 1.2 Customer Grouping

Segment customers for tailored billing (e.g., Residential, Commercial).

[![Customer Groups](https://img.shields.io/badge/Customer_Groups-FFB703?style=for-the-badge&logo=users&logoColor=000)](https://docs.erpnext.com/docs/user/manual/en/customer-group)

#### 💲 1.3 Price Lists & Tariffs

Define rates based on customer type, block rates, or service tiers.

[![Price Lists](https://img.shields.io/badge/Price_Lists-457B9D?style=for-the-badge&logo=pricetag&logoColor=fff)](https://docs.erpnext.com/docs/user/manual/en/price-lists)

### 📊 2. **Billing Operations**

#### 📝 2.1 Service Requests

Flow:

1. Add Request → Survey → BOM → Sales Order
2. Assign new Meter Numbers
3. Auto-create Customer & Meter Linkage

![Service Request Screenshot](https://raw.githubusercontent.com/navariltd/utility-billing/refs/heads/develop/utility_billing/docs/images/utility-service-request.png)

```mermaid
graph TD
    A["Customer / Lead / Prospect (CRM)"] --> B["Create Service Request"]
    B --> C["Create Customer"]
    C --> D["Create Site Survey"]
    D --> H["Create BOM"]
    H --> G
    H --> F
    C --> F["Create Sales Order"]
    C --> G["Create Sales Invoice"]
```

[![👉 Explore Service Request](https://img.shields.io/badge/👉_Explore_Utility_Service_Request-6f42c1?style=for-the-badge&logo=readthedocs&logoColor=fff)](./Service-Request.md)

#### ⛽ 2.2 Meter Reading

Steps:

1. Select Customer
2. Add Utility Item & Enter Current Reading
3. System auto-calculates usage
4. Sales Order is generated on Submit

![Meter Reading Screenshot](https://raw.githubusercontent.com/navariltd/utility-billing/refs/heads/develop/utility_billing/docs/images/meter-reading.png)

```mermaid
graph TD
    A[Service Request] --> B{Meter Reading}
    B --> C[Sales Order]
    C --> D[Sales Invoice]
    D --> E[Payment]
```

[![👉 Explore Meter Reading](https://img.shields.io/badge/👉_Explore_Meter_Reading-6f42c1?style=for-the-badge&logo=readthedocs&logoColor=fff)](./Meter-Reading.md)

#### 🧮 2.3 Mass Billing

Steps:

1. Select multiple Sales Orders
2. Use Menu → "Create Sales Invoice"
3. Background job auto-generates invoices

![Mass Billing Screenshot](https://raw.githubusercontent.com/navariltd/utility-billing/refs/heads/develop/utility_billing/docs/images/mass-billing.png)

### 📌 3. Important Notes

#### 🔧 3.1 Item Configuration

✅ Tick "Is Utility Item" to mark billable services.

![Is Utility Item Screenshot](https://raw.githubusercontent.com/navariltd/utility-billing/refs/heads/develop/utility_billing/docs/images/is_utility_item.png)

#### 📟 3.2 Meter Numbers

Managed as **Serial Numbers**, assigned via **Warranty Claim**.

![Meter Screenshot](https://raw.githubusercontent.com/navariltd/utility-billing/refs/heads/develop/utility_billing/docs/images/meter-number.png)

#### 📟 3.3 Sales Order and Sales Invoice Customizations

The **Sales Order** and **Sales Invoice** Doctypes in ERPNext have been customized to incorporate new fields and sections related to utility billing, meter readings, and service requests

![Sales Order Overview](https://raw.githubusercontent.com/navariltd/utility-billing/refs/heads/develop/utility_billing/docs/images/sales-order.png)
![Sales Invoice Overview](https://raw.githubusercontent.com/navariltd/utility-billing/refs/heads/develop/utility_billing/docs/images/sales-invoice.png)

[![👉 Explore Sales Order and Invoice](https://img.shields.io/badge/👉_Explore_Sales_Order_and_Invoice-6f42c1?style=for-the-badge&logo=readthedocs&logoColor=fff)](./Sales-Order-and-Invoice.md)

## 🚀 Quick Navigation

[![Home](https://img.shields.io/badge/Home-DEF4FF?style=for-the-badge&logo=github&logoColor=000)](https://github.com/navariltd/utility-billing)
[![Full Documentation](https://img.shields.io/badge/Full_Documentation-6366F1?style=for-the-badge&logo=readthedocs&logoColor=fff)](https://github.com/navariltd/utility-billing/wiki)
[![ERPNext Docs](https://img.shields.io/badge/ERPNext_Docs-FF6B6B?style=for-the-badge&logo=erpnext&logoColor=fff)](https://docs.erpnext.com)
[![Frappe Framework](https://img.shields.io/badge/Frappe_Framework-00C49A?style=for-the-badge&logo=frappe&logoColor=fff)](https://frappeframework.com/docs)
[![Community Forum](https://img.shields.io/badge/Community_Forum-F59E0B?style=for-the-badge&logo=discourse&logoColor=fff)](https://discuss.frappe.io)
[![Report Issue](https://img.shields.io/badge/Report_Issue-E63946?style=for-the-badge&logo=githubissues&logoColor=fff)](https://github.com/navariltd/utility-billing/issues)
[![Website](https://img.shields.io/badge/Website-1E293B?style=for-the-badge&logo=googlechrome&logoColor=fff)](https://navari.co.ke)
