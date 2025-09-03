# Copyright (c) 2024, Navari and contributors
# For license information, please see license.txt

import frappe
from frappe.contacts.address_and_contact import load_address_and_contact
from frappe.utils.nestedset import NestedSet

class UtilityProperty(NestedSet):
    def onload(self):
        load_address_and_contact(self)

    def validate(self):
        if self.is_group:
            self.status = ""
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
            # If existing asset is selected, skip asset creation and use existing asset data
            if self.is_existing_asset and self.existing_asset:
                # Get existing asset data to populate fields
                asset_doc = frappe.get_doc("Asset", self.existing_asset)
                if asset_doc.item_code:
                    self.item = asset_doc.item_code
                if asset_doc.location:
                    self.location = asset_doc.location
                if asset_doc.asset_category:
                    self.asset_category = asset_doc.asset_category
                if asset_doc.gross_purchase_amount:
                    self.gross_purchase_amount = asset_doc.gross_purchase_amount
                if asset_doc.purchase_date:
                    self.purchase_date = asset_doc.purchase_date
                # Skip asset creation since we're using existing asset
                return

            # Only create new assets if no existing asset is selected
            if not frappe.db.exists("Item Group", "Fixed Asset"):
                item_group = frappe.db.get_value("Item Group", {"is_group": 1})
                frappe.get_doc({
                    "doctype": "Item Group",
                    "item_group_name": "Fixed Asset",
                    "is_group": 0,
                    "parent_item_group": item_group,
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
                asset_data = {
                    "doctype": "Asset",
                    "item_code": self.item,
                    "company": self.company,
                    "asset_name": self.property_name,
                    "asset_category": self.asset_category,
                    "naming_series": self.asset_naming_series or "ACC-ASS-.YYYY.-",
                    "is_existing_asset": 1,
                    "purchase_date": self.purchase_date or frappe.utils.today(),  # Always set purchase_date
                }
                
                # Only add optional fields if they have values
                if self.gross_purchase_amount:
                    asset_data["gross_purchase_amount"] = self.gross_purchase_amount
                if self.location:
                    asset_data["location"] = self.location
                
                asset_doc = frappe.get_doc(asset_data)
                asset_doc.insert(ignore_permissions=True, ignore_mandatory=True, ignore_links=True)

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
        }).insert(ignore_permissions=True, ignore_mandatory=True, ignore_links=True)

    @frappe.whitelist()
    def update_asset_from_property(self):
        """Fetch information from the existing asset for display purposes only."""
        if not self.existing_asset:
            return {"error": "No existing asset selected"}

        try:
            # Get the asset document
            asset_doc = frappe.get_doc("Asset", self.existing_asset)
            
            # Simply return the asset information without updating the property
            return {
                "message": "Asset information retrieved successfully",
                "asset_status": "submitted" if asset_doc.docstatus == 1 else "draft",
                "asset_data": {
                    "location": asset_doc.location,
                    "asset_category": asset_doc.asset_category,
                    "gross_purchase_amount": asset_doc.gross_purchase_amount,
                    "purchase_date": asset_doc.purchase_date,
                    "asset_name": asset_doc.asset_name,
                    "item_code": asset_doc.item_code,
                    "company": asset_doc.company,
                    "asset_owner": getattr(asset_doc, 'asset_owner', 'Not set'),
                    "custodian": getattr(asset_doc, 'custodian', 'Not set'),
                    "status": getattr(asset_doc, 'status', 'Not set')
                },
                "note": "Asset information is being used as-is. No updates made to utility property."
            }
            
        except Exception as e:
            frappe.log_error(f"Error fetching asset information: {str(e)}")
            return {"error": f"Failed to fetch asset information: {str(e)}"}
