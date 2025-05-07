# 🚪 **Contract Doctype Customizations**

## Overview

The **Contract Doctype** is an essential component in managing tenancy agreements, utility billing, and linking customers with properties. It is designed to streamline the lifecycle of a contract, from service request initiation to property management and billing. These customizations leverage advanced fields such as utility service requests, properties, billing increments, and recurring schedules to automate and manage various aspects of tenancy agreements.

![Utility & Property Overview](https://raw.githubusercontent.com/navariltd/utility-billing/refs/heads/develop/utility_billing/docs/images/contract.png)

## Key Features

- **Utility Service Request**: Link a utility service request to the contract.
- **Properties Management**: Manage multiple properties under one contract.
- **Billing Increments**: Configure automatic rent or service charge increases over time.
- **Recurring Billing**: Set up recurring billing schedules for tenants or property utilities.
- **Contract Start and End Dates**: Automatically fetch start and end dates from the related utility service request to ensure consistency.

## Custom Fields and Functionality

### 1. **Utility Service Request Link**

This field allows you to link the contract to a specific **Utility Service Request**, which provides details about the utility needs of the tenant. This helps to track utility requests and their relationship to the contract.

---

### 2. **Requested Properties Table**

This table allows you to manage multiple utility or rental properties within a single contract. Each property item supports advanced billing and automation features designed to streamline lease and invoice generation processes.

![Utility & Property Overview](https://raw.githubusercontent.com/navariltd/utility-billing/refs/heads/develop/utility_billing/docs/images/service_request_property.png)

- #### Utility Property: Links a specific property to this contract or service request.

- #### Is Active?: Enable or disable this item from billing or invoicing actions.

- #### 📈 **Billing Increment Settings**

  This allows you to configure automatic rent or service charge increases over time for each property:

  - **Increment Frequency**: Set how often the increment should be applied (e.g., Monthly, Quarterly, Yearly).
  - **Increment Interval (Months)**: Define the number of months between each increment (e.g., `12` for yearly, `6` for semi-annual).
  - **Increment Percentage**: The percentage by which the amount increases at each interval. For example, enter `5` to increase by 5% each cycle.

- #### 🔁 **Recurring Billing Schedule**

  This section automates recurring billing based on contract terms for properties:

  - **Frequency**: Choose how often to generate recurring invoices (e.g., Monthly, Quarterly).
  - **Repeat on Day**: For monthly/quarterly frequencies, specify the exact day (e.g., 5 for the 5th of each month).
  - **Repeat on Last Day of the Month**: Automatically sets recurrence to the last day of the month, no matter the month's length.
  - **Submit on Creation**: Automatically submits the generated document on creation, useful for seamless billing workflows.

- #### 📅 **Date Constraints**

  - **Start Date / End Date**: Defines the period during which the utility contract or billing should remain active for the property. These dates are validated against the utility service request to ensure consistency.

---

### 4. **Start and End Dates**

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
