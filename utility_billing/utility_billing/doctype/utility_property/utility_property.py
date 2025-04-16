# Copyright (c) 2024, Navari and contributors
# For license information, please see license.txt

from frappe.contacts.address_and_contact import load_address_and_contact
from frappe.utils.nestedset import NestedSet
import frappe

class UtilityProperty(NestedSet):
    def onload(self):
        load_address_and_contact(self)

    def validate(self):
        if self.is_fixed_asset:
            if not frappe.db.exists("Item Group", "Fixed Asset"):
                frappe.get_doc({
                    "doctype": "Item Group",
                    "item_group_name": "Fixed Asset",
                    "is_group": 0,
                    "parent_item_group": "All Item Groups"
                }).insert()

            if not self.item:
                item_doc = frappe.get_doc({
                    "doctype": "Item",
                    "item_code": self.property_name,
                    "item_name": self.property_name,
                    "is_fixed_asset": 1,
                    "is_stock_item": 0,
                    "item_group": "Fixed Asset",
                    "asset_category": self.asset_category,
                    "stock_uom": "Nos"
                })
                item_doc.insert()
                self.item = item_doc.name

            asset_exists = frappe.db.exists("Asset", {
                "item_code": self.item,
                "utility_property": self.name
            })
            if not asset_exists:
                asset_doc = frappe.get_doc({
                    "doctype": "Asset",
                    "item_code": self.item,
                    "asset_name": self.property_name,
                    "asset_category": self.asset_category,
                    "naming_series": self.asset_naming_series or "ACC-ASS-.YYYY.-",
                    "utility_property": self.name,
                    "is_existing_asset": 1,
                    "gross_purchase_amount": self.gross_purchase_amount,
                    "location": self.location
                })
                asset_doc.insert()
