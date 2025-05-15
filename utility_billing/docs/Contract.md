# 🚪 **Contract Doctype Customizations**

## Overview

The **Contract Doctype** is an essential component in managing tenancy agreements, utility billing, and linking customers with properties. It is designed to streamline the lifecycle of a contract, from service request initiation to property management and billing. These customizations leverage advanced fields such as utility service requests, properties, billing increments, and recurring schedules to automate and manage various aspects of tenancy agreements.

![Utility & Property Overview](https://raw.githubusercontent.com/navariltd/utility-billing/refs/heads/develop/utility_billing/docs/images/contract.png)

## Key Features

- **Utility Service Request**: Link a utility service request to the contract.
- **Properties Management**: Manage multiple properties under one contract.
- **Billing Adjustment Rule**: Set up rules for automatic billing adjustments, such as rent or service charge increments, late payment penalties, or other recurring changes. This feature enables you to configure and automate complex billing scenarios for tenants or property utilities.
- **Contract Start and End Dates**: Automatically fetch start and end dates from the related utility service request to ensure consistency.

## Custom Fields and Functionality

### 1. **Utility Service Request Link**

This field allows you to link the contract to a specific **Utility Service Request**, which provides details about the utility needs of the tenant. This helps to track utility requests and their relationship to the contract.

---

### 2. **Requested Properties Table**

This table is used to associate multiple utility or rental properties with a service contract. Each row defines a specific property's billing configuration, activation status, billing rule, and contract period.

![Utility & Property Overview](https://raw.githubusercontent.com/navariltd/utility-billing/refs/heads/develop/utility_billing/docs/images/service_request_property.png)

- #### 🏘️ **Utility Property**

  A required field that links to the specific property associated with this contract item.

- #### ✅ **Is Active?**

  Indicates whether the property is currently active for billing. Uncheck to temporarily disable invoicing or adjustments for the item.

- #### 📅 **Start Date / End Date**

  Defines the contract duration for the property. Billing and adjustments are only applied within this date range.

- #### 📐 **Contract Length (Months)**

  Automatically calculated or manually defined, this represents the total duration of the contract in months. Useful for internal reporting or rule application.

- #### ⚙️ **Adjustment Rule**

  Links to a `Billing Adjustment Rule`, which determines how rates change over time (e.g., percentage-based rent increments or conditional adjustments).

## [![👉 Billing Adjustment Rule](https://img.shields.io/badge/👉_Billing_Adjustment_Rule-6f42c1?style=for-the-badge&logo=readthedocs&logoColor=fff)](./Billing-Adjustment-Rule.md)

---

### 3. **Start and End Dates**

The **Start Date** and **End Date** fields for the contract are automatically fetched from the linked **Utility Service Request**. This ensures that the contract is aligned with the actual service request and avoids inconsistencies between the requested service and contract duration.

---

## 🚀 Quick Navigation

[![Home](https://img.shields.io/badge/Home-DEF4FF?style=for-the-badge&logo=github&logoColor=000)](https://github.com/navariltd/utility-billing)
[![Full Documentation](https://img.shields.io/badge/Full_Documentation-6366F1?style=for-the-badge&logo=readthedocs&logoColor=fff)](https://github.com/navariltd/utility-billing/wiki)
[![ERPNext Docs](https://img.shields.io/badge/ERPNext_Docs-FF6B6B?style=for-the-badge&logo=erpnext&logoColor=fff)](https://docs.erpnext.com)
[![Frappe Framework](https://img.shields.io/badge/Frappe_Framework-00C49A?style=for-the-badge&logo=frappe&logoColor=fff)](https://frappeframework.com/docs)
[![Community Forum](https://img.shields.io/badge/Community_Forum-F59E0B?style=for-the-badge&logo=discourse&logoColor=fff)](https://discuss.frappe.io)
[![Report Issue](https://img.shields.io/badge/Report_Issue-E63946?style=for-the-badge&logo=githubissues&logoColor=fff)](https://github.com/navariltd/utility-billing/issues)
[![Website](https://img.shields.io/badge/Website-1E293B?style=for-the-badge&logo=googlechrome&logoColor=fff)](https://navari.co.ke)
