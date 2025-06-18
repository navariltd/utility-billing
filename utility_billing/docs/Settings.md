## ⚙️ Utility Billing Settings

The **Utility Billing Settings** Doctype centralizes critical configuration options for managing automation, service flows, customer onboarding, penalties, and document creation in ERPNext.

![Utility Settings Screenshot](https://raw.githubusercontent.com/navariltd/utility-billing/refs/heads/develop/utility_billing/docs/images/utility-settings.png)

---

### 📦 Sales & Stock Settings

| **Field**                                                        | **Description**                                                                                     |
| ---------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| **Sales Order Creation State**                                   | Sets whether Sales Orders are created in `Draft` or `Submitted` state during utility workflows.     |
| **Stock Entry Creation State**                                   | Determines the default state (`Draft` or `Submitted`) of Stock Entries linked to utility processes. |
| **Create single invoice for multiple sales orders per customer** | If enabled, merges multiple Sales Orders for a customer into a single Sales Invoice.                |
| **Sales Invoice Creation State**                                 | Specifies if Sales Invoices are automatically created as `Draft` or `Submitted`.                    |

---

### 📝 Service Request Settings

| **Field**                                                  | **Description**                                                                                       |
| ---------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| **Create Customer from Utility Service Request on Submit** | Automatically creates a Customer when a Utility Service Request is submitted.                         |
| **Enable Adding Extra Rows for SO/SI Creation**            | Allows extra table rows for complex billing structures when generating Sales Orders or Invoices.      |
| **Enable Site Survey**                                     | Enables site surveys as part of the utility request process before generating contracts or documents. |
| **Require Deposit Before Contract Creation**               | Prevents contract creation unless a deposit is received.                                              |
| **Require Contract Before Sales Invoice Creation**         | Blocks invoice generation unless a valid contract exists.                                             |

---

### 🧪 Demo Data

| **Field**              | **Description**                                              |
| ---------------------- | ------------------------------------------------------------ |
| **Generate Demo Data** | Creates sample utility billing records for testing purposes. |
| **Clear Demo Data**    | Removes all previously generated demo data from the system.  |

---

## 🚀 Quick Navigation

[![Home](https://img.shields.io/badge/Home-DEF4FF?style=for-the-badge&logo=github&logoColor=000)](https://github.com/navariltd/utility-billing)
[![Full Documentation](https://img.shields.io/badge/Full_Documentation-6366F1?style=for-the-badge&logo=readthedocs&logoColor=fff)](https://github.com/navariltd/utility-billing/wiki)
[![ERPNext Docs](https://img.shields.io/badge/ERPNext_Docs-FF6B6B?style=for-the-badge&logo=erpnext&logoColor=fff)](https://docs.erpnext.com)
[![Frappe Framework](https://img.shields.io/badge/Frappe_Framework-00C49A?style=for-the-badge&logo=frappe&logoColor=fff)](https://frappeframework.com/docs)
[![Community Forum](https://img.shields.io/badge/Community_Forum-F59E0B?style=for-the-badge&logo=discourse&logoColor=fff)](https://discuss.frappe.io)
[![Report Issue](https://img.shields.io/badge/Report_Issue-E63946?style=for-the-badge&logo=githubissues&logoColor=fff)](https://github.com/navariltd/utility-billing/issues)
[![Website](https://img.shields.io/badge/Website-1E293B?style=for-the-badge&logo=googlechrome&logoColor=fff)](https://navari.co.ke)
