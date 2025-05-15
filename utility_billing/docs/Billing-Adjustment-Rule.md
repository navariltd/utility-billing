# ⚖️ **Billing Adjustment Rule**

## Overview

The **Billing Adjustment Rule Doctype** is designed to streamline and automate billing increments, penalty assessments, and accounting configurations for utility billing or property rental scenarios. This doctype supports advanced configurations like recurring increment settings, penalty calculations, and accounting linkages to ensure full financial control across contracts and tenant agreements.

![Billing Adjustment Rule Overview](https://raw.githubusercontent.com/navariltd/utility-billing/develop/utility_billing/docs/images/adjustment_rule.png)

![Billing Adjustment Rule Overview](https://raw.githubusercontent.com/navariltd/utility-billing/develop/utility_billing/docs/images/adjustment_rule_2.png)

## Key Features

- **Increment Settings**: Automate periodic rent or service charge adjustments.
- **Penalty Settings**: Configure penalties for overdue payments, including grace periods and compounding options.
- **Accounting Integration**: Link specific income and receivable accounts for adjustments and penalties.
- **Control and Limits**: Enforce caps, basis of calculation, and optional write-offs for financial accuracy.

---

## 🔧 Custom Fields and Functionality

### 1. **Basic Rule Details**

- **Rule Name**: Unique identifier for each adjustment rule.
- **Disabled**: Toggle to activate or deactivate the rule without deleting it.

---

### 2. 📈 **Increment Settings**

These fields manage automated billing increases for long-term contracts:

- **Increment Frequency**: Defines how often adjustments occur.
- **Increment Interval (Months)**: Interval in months between each adjustment (e.g., `12` for yearly).
- **Increment Percentage**: Percentage by which the amount is increased at each interval.
- **Effective After (Months)**: Number of months after the start date when adjustments begin.
- **Maximum Billing Adjustment Cap (%)**: Limits the adjustment percentage regardless of frequency.
- **Billing Adjustment Basis**: Choose between _Original Amount_ or _Last Adjusted Amount_ for future calculations.

![Increment Settings](https://raw.githubusercontent.com/navariltd/utility-billing/develop/utility_billing/docs/images/adjustment_rule_2.png)

---

### 3. 🔁 **Penalty Settings**

Penalties can be customized for overdue payments based on tenant behavior and grace periods.

- **Grace Period (Days)**: Days after due date before penalties apply.
- **Penalty Type**: Choose between _Fixed Amount_ or _Percentage_.
- **Penalty Value**: The actual amount or percentage charged as a penalty.
- **Maximum Penalty Cap**: Caps the penalty to a maximum value.
- **Penalty Frequency**: Determines how often penalties are charged (e.g., Daily, Weekly, Monthly).
- **Compounding Penalty**: Enable if penalties should increase over time.
- **Submit Penalty Invoice**: Automatically submits the penalty invoice upon creation.

---

### 4. 🧾 **Accounting Settings**

Directly connect adjustments and penalties with your ERP accounting system:

- **Penalty Income Account**: Account where penalty revenue is recognized.
- **Penalty Receivable Account**: Account for tracking receivables from penalties.
- **Billing Adjustment Income Account**: Income account to post increment adjustments.
- **Write-Off Account**: For adjustments that need to be written off.

---

### 5. 📝 **Additional Information**

- **Description**: Use this section to explain the purpose or specific use case of the rule.

---

## 🚀 Quick Navigation

[![Home](https://img.shields.io/badge/Home-DEF4FF?style=for-the-badge&logo=github&logoColor=000)](https://github.com/navariltd/utility-billing)
[![Full Documentation](https://img.shields.io/badge/Full_Documentation-6366F1?style=for-the-badge&logo=readthedocs&logoColor=fff)](https://github.com/navariltd/utility-billing/wiki)
[![ERPNext Docs](https://img.shields.io/badge/ERPNext_Docs-FF6B6B?style=for-the-badge&logo=erpnext&logoColor=fff)](https://docs.erpnext.com)
[![Frappe Framework](https://img.shields.io/badge/Frappe_Framework-00C49A?style=for-the-badge&logo=frappe&logoColor=fff)](https://frappeframework.com/docs)
[![Community Forum](https://img.shields.io/badge/Community_Forum-F59E0B?style=for-the-badge&logo=discourse&logoColor=fff)](https://discuss.frappe.io)
[![Report Issue](https://img.shields.io/badge/Report_Issue-E63946?style=for-the-badge&logo=githubissues&logoColor=fff)](https://github.com/navariltd/utility-billing/issues)
[![Website](https://img.shields.io/badge/Website-1E293B?style=for-the-badge&logo=googlechrome&logoColor=fff)](https://navari.co.ke)
