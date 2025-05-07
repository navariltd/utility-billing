# 📘 Utility Property

The **Utility Property** DocType is designed for managing real estate units and buildings within an ERP system. It supports both basic property definitions and advanced features like fixed asset linkage, unit-level tracking, features and amenities, hierarchical grouping, and location-based categorization.

![Utility & Property Overview](https://raw.githubusercontent.com/navariltd/utility-billing/refs/heads/develop/utility_billing/docs/images/uility_property.png)

The Utility Property DocType allows you to:

- Register properties and units (apartments, houses, offices, etc.)
- Organize them in hierarchical groups (buildings, estates)
- Optionally treat properties as **fixed assets**
- Attach unit-specific details, amenities, and legal info
- Dynamically link to company, location, territory, and utility categories

---

## 📁 Field Structure & Sections

### **Basic Information**

- `property_name` (required, unique): Name of the property/unit
- `company`: Owning or managing company
- `utility_category`: Utility category this property belongs to
- `status`: Availability (Available, Occupied, Under Maintenance, Reserved)
- `territory`: Business territory
- `is_group`: Check if this is a parent property or group

---

## 🏗️ Asset Management _(Optional)_

Enable the `is_fixed_asset` checkbox to treat the property as a fixed asset. Once enabled, the following fields become relevant:

- `asset_category`: Asset category of the property
- `item`: Linked item (must be marked as a fixed asset)
- `asset_naming_series`: Series used when creating the asset
- `gross_purchase_amount`: Asset purchase value

> 💡 If `item` is selected, `asset_category` and `gross_purchase_amount` become read-only and auto-linked.

---

## 📍 Location Details

- `location`: Geographical location or estate (linked DocType)
- `plot_no`, `house_no`, `lot_size`: Land-related details

---

## 🏢 Unit Information

Track information about the internal structure or units:

- `unit_number`: Unique number for the unit
- `unit_type`: Type (e.g., Studio, 2BHK, Office)
- `bedrooms`, `bathrooms`
- `floor_level`, `unit_size`

---

## ✨ Features and Amenities

- `features`: A child table of `Utility Property Feature Item`
- Allows listing multiple features like swimming pool, balcony, parking, etc.

---

## 📚 Additional Info

- `unique_features`: Free text for any distinct selling points
- `legal_description`: Legal terms or property registration info

---

## 🚀 Quick Navigation

[![Home](https://img.shields.io/badge/Home-DEF4FF?style=for-the-badge&logo=github&logoColor=000)](https://github.com/navariltd/utility-billing)
[![Full Documentation](https://img.shields.io/badge/Full_Documentation-6366F1?style=for-the-badge&logo=readthedocs&logoColor=fff)](https://github.com/navariltd/utility-billing/wiki)
[![ERPNext Docs](https://img.shields.io/badge/ERPNext_Docs-FF6B6B?style=for-the-badge&logo=erpnext&logoColor=fff)](https://docs.erpnext.com)
[![Frappe Framework](https://img.shields.io/badge/Frappe_Framework-00C49A?style=for-the-badge&logo=frappe&logoColor=fff)](https://frappeframework.com/docs)
[![Community Forum](https://img.shields.io/badge/Community_Forum-F59E0B?style=for-the-badge&logo=discourse&logoColor=fff)](https://discuss.frappe.io)
[![Report Issue](https://img.shields.io/badge/Report_Issue-E63946?style=for-the-badge&logo=githubissues&logoColor=fff)](https://github.com/navariltd/utility-billing/issues)
[![Website](https://img.shields.io/badge/Website-1E293B?style=for-the-badge&logo=googlechrome&logoColor=fff)](https://navari.co.ke)
