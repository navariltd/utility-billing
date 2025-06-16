# Copyright (c) 2024, Navari and contributors
# For license information, please see license.txt

import frappe
from frappe.contacts.address_and_contact import load_address_and_contact
from frappe.utils.nestedset import NestedSet

class UtilityProperty(NestedSet):
    def onload(self):
        load_address_and_contact(self)

    def validate(self):
        if self.item:
            asset = frappe.db.get_value(
                "Asset",
                {
                    "item_code": self.item,
                    "asset_name": self.property_name
                },
                ["location", "asset_category", "gross_purchase_amount"],
                as_dict=True
            )
            if asset:
                self.location = asset.location
                self.asset_category = asset.asset_category
                self.gross_purchase_amount = asset.gross_purchase_amount

        if self.is_fixed_asset:
            if not frappe.db.exists("Item Group", "Fixed Asset"):
                frappe.get_doc({
                    "doctype": "Item Group",
                    "item_group_name": "Fixed Asset",
                    "is_group": 0,
                    "parent_item_group": "All Item Groups"
                }).insert()

            if not self.item:
                if frappe.db.exists("Item", {"item_code": self.property_name}):
                    self.item = self.property_name
                else:
                    item_doc = self._create_item()
                    self.item = item_doc.name
            else:
                if not frappe.db.exists("Item", self.item):
                    item_doc = self._create_item()
                    self.item = item_doc.name

            if not frappe.db.exists("Asset", {
                "item_code": self.item,
                "asset_name": self.property_name,
            }):
                frappe.db.set_value("Item", self.item, "disabled", 0)
                asset_doc = frappe.get_doc({
                    "doctype": "Asset",
                    "item_code": self.item,
                    "asset_name": self.property_name,
                    "asset_category": self.asset_category,
                    "naming_series": self.asset_naming_series or "ACC-ASS-.YYYY.-",
                    "is_existing_asset": 1,
                    "gross_purchase_amount": self.gross_purchase_amount, 
                    "purchase_date": self.purchase_date, 
                    "location": self.location
                })
                asset_doc.insert()

    def _create_item(self):
        """Helper method to create a new item document."""
        return frappe.get_doc({
            "doctype": "Item",
            "item_code": self.property_name,
            "item_name": self.property_name,
            "is_fixed_asset": 1,
            "is_stock_item": 0,
            "item_group": "Fixed Asset",
            "asset_category": self.asset_category,
            "is_sales_item": 1,
            "is_utility_item": 1,
            "stock_uom": "Nos",
            "disabled": 0,
        }).insert(ignore_permissions=True)
