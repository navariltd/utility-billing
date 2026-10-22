# Copyright (c) 2024, Navari and contributors
# For license information, please see license.txt

"""Utility Property controller.

Properties are both physical units and, when ``is_fixed_asset`` is set,
fixed assets. Every billable unit additionally owns a service item named
after the property, created on demand by
``utility_billing.utility_billing.utils.service_item`` and used as the rent
billing item, and may own a Cost Center for tracking its rent and expenses,
created on demand by ``utility_billing.utility_billing.utils.cost_center``.
The Cost Center is synced onto the service item's own Item Defaults, so
Sales Invoice lines billing that item pick it up automatically.
"""

import frappe
from frappe import _
from frappe.contacts.address_and_contact import load_address_and_contact
from frappe.utils.nestedset import NestedSet

from utility_billing.utility_billing.utils.cost_center import (
    ensure_property_cost_center,
    sync_cost_center_to_service_item,
)
from utility_billing.utility_billing.utils.service_item import (
    create_service_item_for_property,
)


class UtilityProperty(NestedSet):
    def onload(self):
        load_address_and_contact(self)

    def validate(self):
        if self.is_group:
            self.status = ""
        self.set_service_item()
        self.validate_cost_center()
        self.set_cost_center()
        self.sync_service_item_cost_center()

        if self.item:
            asset = frappe.db.get_value(
                "Asset",
                {
                    "item_code": self.item,
                    "asset_name": self.property_name
                },
                ["location", "asset_category", "net_purchase_amount"],
                as_dict=True
            )
            if asset:
                self.location = asset.location
                self.asset_category = asset.asset_category
                self.net_purchase_amount = asset.net_purchase_amount

        if self.is_fixed_asset:
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
                asset_doc = frappe.get_doc({
                    "doctype": "Asset",
                    "item_code": self.item,
                    "company": self.company,
                    "asset_name": self.property_name,
                    "asset_category": self.asset_category,
                    "naming_series": self.asset_naming_series or "ACC-ASS-.YYYY.-",
                    "is_existing_asset": 1,
                    "net_purchase_amount": self.net_purchase_amount, 
                    "purchase_date": self.purchase_date, 
                    "location": self.location
                })
                asset_doc.insert(ignore_permissions=True, ignore_mandatory=True, ignore_links=True)

    def set_service_item(self):
        """Ensure the property has a rent billing service item.

        The item is only created for billable leaf properties. Failures are
        logged instead of raised so that a missing item group configuration
        never blocks saving a property.
        """
        if self.is_group:
            return

        if self.service_item and frappe.db.exists("Item", self.service_item):
            return

        try:
            item_code = create_service_item_for_property(self)
        except Exception:
            frappe.log_error(
                frappe.get_traceback(),
                f"Could not create service item for property {self.name}",
            )
            return

        if item_code:
            self.service_item = item_code

    def validate_cost_center(self):
        """Validate a manually chosen Cost Center.

        The client filters this field to leaves of the right company, but
        that is UX only - this is the actual guarantee.
        """
        if self.is_group:
            return

        if self.cost_center:
            self.validate_cost_center_is_leaf()

    def validate_cost_center_is_leaf(self):
        is_group, company = frappe.db.get_value(
            "Cost Center", self.cost_center, ["is_group", "company"]
        )

        if is_group:
            frappe.throw(
                _("{0} is a Group Cost Center and cannot be used as a leaf Cost Center.").format(
                    frappe.bold(self.cost_center)
                )
            )

        if self.company and company != self.company:
            frappe.throw(
                _("Cost Center {0} belongs to {1}, not {2}.").format(
                    frappe.bold(self.cost_center), company, self.company
                )
            )

    def set_cost_center(self):
        """Ensure the property has a Cost Center for tracking rent and expenses.

        Only created for billable leaf properties. Failures are logged instead
        of raised so that a missing settings configuration never blocks saving
        a property.
        """
        if self.is_group:
            return

        if self.cost_center and frappe.db.exists("Cost Center", self.cost_center):
            return

        try:
            cost_center = ensure_property_cost_center(self)
        except Exception:
            frappe.log_error(
                frappe.get_traceback(),
                f"Could not create Cost Center for property {self.name}",
            )
            return

        if cost_center:
            self.cost_center = cost_center

    def sync_service_item_cost_center(self):
        """Sync this property's Cost Center onto its service item's Item Defaults.

        Only fills a company's row when it has no Cost Center yet - an
        existing value is left alone. Failures are logged instead of raised so
        a missing service item or Item Defaults quirk never blocks saving.
        """
        if self.is_group:
            return

        try:
            sync_cost_center_to_service_item(self)
        except Exception:
            frappe.log_error(
                frappe.get_traceback(),
                f"Could not sync Cost Center to service item for property {self.name}",
            )

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
        