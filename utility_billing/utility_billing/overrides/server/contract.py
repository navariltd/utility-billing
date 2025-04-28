import frappe
from frappe import _
from frappe.model.document import Document
from utility_billing.utility_billing.utils.auto_repeat import cancel_auto_repeats_for_property


@frappe.whitelist()
def before_submit(doc: Document, method: str) -> None:
    for entry in doc.properties:
        utility_property = entry.utility_property
        if utility_property and entry.is_active:
            status = frappe.db.get_value("Utility Property", utility_property, "status")
            if status != "Available":
                frappe.throw(_("Utility Property {0} is not available. Current status: {1}. It must be available to submit the contract.").format(utility_property, status))
            else:
                frappe.db.set_value("Utility Property", utility_property, "status", "Occupied")


@frappe.whitelist()
def on_cancel(doc: Document, method: str) -> None:
    for entry in doc.properties:
        utility_property = entry.utility_property
        if utility_property and entry.is_active:
            cancel_auto_repeats_for_property(utility_property)
            frappe.db.set_value("Utility Property", utility_property, "status", "Available")
            

@frappe.whitelist()
def on_update_after_submit(doc: Document, method: str) -> None:
    previous_doc = doc.get_doc_before_save()
    status_changed = doc.has_value_changed("status")
    current_status = doc.status

    for entry in doc.properties:
        utility_property = entry.utility_property
        if not utility_property:
            continue

        if current_status == "Active" and entry.is_active:
            frappe.db.set_value("Utility Property", utility_property, "status", "Occupied")
            continue

        should_set_available = (
            (status_changed and previous_doc.status == "Active" and entry.is_active) or
            (not status_changed and entry.has_value_changed("is_active") and not entry.is_active)
        )

        if should_set_available:
            cancel_auto_repeats_for_property(utility_property)
            frappe.db.set_value("Utility Property", utility_property, "status", "Available")


