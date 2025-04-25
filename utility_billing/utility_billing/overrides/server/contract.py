import frappe
from frappe import _
from typing import List, Dict
from frappe.model.document import Document


@frappe.whitelist()
def before_submit(doc: Document, method: str) -> None:
    for entry in doc.properties: 
        utility_property = entry.utility_property
        if utility_property:
            status = frappe.db.get_value("Utility Property", utility_property, "status")
            if status != "Available":
                frappe.throw(_("Utility Property {0} is not available. Current status: {1}. It must be available to submit the contract.").format(utility_property, status))
            else:
                frappe.db.set_value("Utility Property", utility_property, "status", "Occupied")


@frappe.whitelist()
def on_cancel(doc: Document , method: str) -> None:
    for entry in doc.properties: 
        utility_property = entry.utility_property
        if utility_property:
            frappe.db.set_value("Utility Property", utility_property, "status", "Available")

