import frappe
from frappe import _
from frappe.model.document import Document


@frappe.whitelist()
def validate(doc: Document, method: str) -> None:
    if not doc.item_group:
        frappe.throw(_("Item Group is required"))
    item_group = frappe.get_doc("Item Group", doc.item_group)
    if (
        not item_group.is_utility_item_group
        and item_group.name != "Fixed Asset"
        and doc.is_utility_item
    ):
        frappe.throw(_("Item Group must be a Utility Item Group for Utility Items"))
