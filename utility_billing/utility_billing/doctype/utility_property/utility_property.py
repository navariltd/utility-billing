# Copyright (c) 2024, Navari and contributors
# For license information, please see license.txt

import frappe
from frappe.contacts.doctype.address.address_and_contact import load_address_and_contact
from frappe.utils.nestedset import NestedSet

# Constants for better maintainability
DEFAULT_NAMING_SERIES = "ACC-ASS-.YYYY.-"
FIXED_ASSET_GROUP = "Fixed Asset"

class UtilityProperty(NestedSet):
    def onload(self):
        """Load address and contact information on form load."""
        load_address_and_contact(self)

    def validate(self):
        """Validate property and handle asset logic."""
        if self.is_group:
            self.status = ""
            return  # No further validation for groups

        # Validate required fields for fixed assets
        if self.is_fixed_asset:
            self._validate_required_fields()

        # If item is set, try to fetch asset info and populate fields
        if self.item:
            asset = frappe.db.get_value(
                "Asset",
                {"item_code": self.item, "asset_name": self.property_name},
                ["location", "asset_category", "gross_purchase_amount", "purchase_date"],
                as_dict=True
            )
            if asset:
                self._populate_fields_from_asset(asset)
                return  # Skip further processing if asset found

        if self.is_fixed_asset:
            # If using an existing asset, populate fields and skip creation
            if self.is_existing_asset and self.existing_asset:
                try:
                    asset_doc = frappe.get_doc("Asset", self.existing_asset)
                    self._populate_fields_from_asset(asset_doc)
                    self.disable_asset_fields = 1  # Flag for UI to disable fields
                except frappe.DoesNotExistError:
                    frappe.throw(f"Asset '{self.existing_asset}' does not exist.")
                return  # Skip asset creation

            # Only create new asset if no existing asset is selected
            if not frappe.db.exists("Item Group", FIXED_ASSET_GROUP):
                frappe.throw(f"Item Group '{FIXED_ASSET_GROUP}' does not exist. Please create it first.")

            # Create item if not exists
            if not frappe.db.exists("Item", self.property_name):
                self._create_item()

            # Create asset if not exists (improved check)
            if not frappe.db.exists("Asset", {"item_code": self.property_name}):
                self._create_asset()

    def _validate_required_fields(self):
        """Validate required fields before asset operations."""
        required_fields = ["company", "asset_category"]
        for field in required_fields:
            if not getattr(self, field, None):
                frappe.throw(f"Field '{field}' is required for fixed assets.")

    def _populate_fields_from_asset(self, asset):
        """Populate property fields from asset document or dict, avoiding empty values."""
        field_mappings = {
            "location": "location",
            "asset_category": "asset_category",
            "gross_purchase_amount": "gross_purchase_amount",
            "purchase_date": "purchase_date"
        }
        for prop_field, asset_field in field_mappings.items():
            value = getattr(asset, asset_field, None) or asset.get(asset_field)
            if value:  # Only set if value exists
                setattr(self, prop_field, value)

    def _create_item(self):
        """Create a new Item document for the property."""
        try:
            frappe.get_doc({
                "doctype": "Item",
                "item_code": self.property_name,
                "item_name": self.property_name,
                "is_fixed_asset": 1,
                "is_stock_item": 0,
                "item_group": FIXED_ASSET_GROUP,
                "asset_category": self.asset_category,
                "is_sales_item": 1,
                "is_utility_item": 1,
                "stock_uom": "Nos",
                "disabled": 0,
            }).insert(ignore_permissions=True, ignore_mandatory=True, ignore_links=True)
        except Exception as e:
            frappe.throw(f"Failed to create Item: {str(e)}")

    def _create_asset(self):
        """Create a new Asset document for the property."""
        try:
            naming_series = self.asset_naming_series or DEFAULT_NAMING_SERIES
            if not frappe.db.exists("Naming Series", naming_series):
                frappe.throw(f"Naming Series '{naming_series}' does not exist.")
            
            frappe.get_doc({
                "doctype": "Asset",
                "asset_name": self.property_name,
                "item_code": self.property_name,
                "asset_category": self.asset_category,
                "company": self.company,
                "location": self.location,
                "gross_purchase_amount": self.gross_purchase_amount,
                "purchase_date": self.purchase_date,
                "naming_series": naming_series,
                "status": "Draft",
            }).insert(ignore_permissions=True, ignore_mandatory=True, ignore_links=True)
        except Exception as e:
            frappe.throw(f"Failed to create Asset: {str(e)}")

    @frappe.whitelist()
    def update_asset_from_property(self):
        """
        Fetch information from the existing asset for display only.
        Does not update the property or asset.
        """
        if not self.existing_asset:
            frappe.throw("No existing asset selected.")

        try:
            asset_doc = frappe.get_doc("Asset", self.existing_asset)
            return {
                "message": "Asset information retrieved successfully.",
                "asset_data": {
                    "asset_name": asset_doc.asset_name,
                    "location": asset_doc.location,
                    "asset_category": asset_doc.asset_category,
                    "gross_purchase_amount": asset_doc.gross_purchase_amount,
                    "purchase_date": asset_doc.purchase_date,
                    "item_code": asset_doc.item_code,
                    "company": asset_doc.company,
                    "asset_owner": asset_doc.asset_owner,
                    "custodian": asset_doc.custodian,
                    "status": asset_doc.status,
                },
                "note": "Asset information is being used as-is. No updates made to utility property."
            }
        except frappe.DoesNotExistError:
            frappe.throw(f"Asset '{self.existing_asset}' does not exist.")
        except Exception as e:
            frappe.throw(f"Error retrieving asset information: {str(e)}")

    def on_update(self):
        """Set read-only properties based on existing asset selection (handled in JS)."""
        pass  # UI logic should be handled in client-side JS
