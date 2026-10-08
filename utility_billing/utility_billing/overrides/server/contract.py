import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, getdate
from utility_billing.utility_billing.utils.auto_repeat import cancel_auto_repeats_for_property

ROW_DOCTYPE = "Contract Utility Property Item"

# Copied from the Utility Service Request by create_contract, never edited on the Contract.
# Is Active stays editable: unticking it frees the property and cancels its Auto Repeats.
LOCKED_ROW_FIELDS = (
    "utility_property",
    "item_code",
    "start_date",
    "end_date",
    "contract_length_months",
    "adjustment_rule",
    "insurance",
)
DATE_FIELDS = {"start_date", "end_date"}
FLOAT_FIELDS = {"contract_length_months"}


def validate(doc: Document, method: str) -> None:
    if doc.is_new():
        check_new_contract(doc)
    else:
        check_rows_unchanged(doc, get_saved_contract(doc))


def before_update_after_submit(doc: Document, method: str) -> None:
    check_rows_unchanged(doc, get_saved_contract(doc))


def get_saved_contract(doc: Document) -> Document:
    return doc.get_doc_before_save() or frappe.get_doc(doc.doctype, doc.name)


def check_new_contract(doc) -> None:
    """Allow properties and a request link only on a Contract made by ``create_contract``.

    ``create_contract`` sets ``flags.from_service_request``. Flags are never read
    from a request payload, so a Contract posted through the API cannot claim it.
    A Contract without either stays a plain ERPNext Contract.

    Raises:
        frappe.ValidationError: When the Contract is amended, or was not made
            from its Utility Service Request.
    """
    if not (doc.get("properties") or doc.get("utility_service_request")):
        return

    if doc.get("amended_from"):
        frappe.throw(
            _(
                "Contract {0} has properties from a Utility Service Request, so it cannot be "
                "amended. Create a new Contract from the Utility Service Request instead."
            ).format(frappe.bold(doc.amended_from))
        )

    if not doc.flags.from_service_request:
        frappe.throw(
            _(
                "A Contract's properties come from its Utility Service Request. Create the "
                "Contract from the Utility Service Request instead."
            )
        )


def check_rows_unchanged(doc, saved) -> None:
    """Block adding, removing or editing the properties copied from the request.

    Compared with the saved Contract, not the request: a request edited after
    its Contract was made leaves the Contract as it is, and the mismatch is
    caught when invoicing.

    Raises:
        frappe.ValidationError: Naming the request link, row or field changed.
    """
    if (doc.get("utility_service_request") or None) != (saved.get("utility_service_request") or None):
        frappe.throw(_("The Utility Service Request of a Contract cannot be changed."))

    saved_rows = {row.name: row for row in saved.get("properties") or []}
    meta = frappe.get_meta(ROW_DOCTYPE)

    for row in doc.get("properties") or []:
        saved_row = saved_rows.get(row.name)
        if not saved_row:
            frappe.throw(
                _(
                    "Row #{0}: Properties cannot be added to a Contract. They are copied from "
                    "its Utility Service Request."
                ).format(row.idx)
            )

        for fieldname in LOCKED_ROW_FIELDS:
            if normalise(fieldname, row.get(fieldname)) != normalise(fieldname, saved_row.get(fieldname)):
                frappe.throw(
                    _(
                        "Row #{0}: {1} cannot be changed. It is copied from the Utility Service "
                        "Request."
                    ).format(row.idx, frappe.bold(_(meta.get_label(fieldname))))
                )

        if saved.get("docstatus") == 1 and cint(row.get("is_active")) and not cint(saved_row.get("is_active")):
            frappe.throw(
                _(
                    "Row #{0}: Utility Property {1} cannot be activated again once the Contract "
                    "is submitted."
                ).format(row.idx, frappe.bold(row.utility_property))
            )

    names = {row.name for row in doc.get("properties") or []}
    removed = [row.utility_property for row in saved_rows.values() if row.name not in names]
    if removed:
        frappe.throw(
            _("Properties cannot be removed from a Contract: {0}.").format(
                ", ".join(frappe.bold(name) for name in removed)
            )
        )


def normalise(fieldname: str, value):
    """Return a row value in one form, whether read from the database or a form."""
    if fieldname in DATE_FIELDS:
        return getdate(value) if value else None
    if fieldname in FLOAT_FIELDS:
        return flt(value)

    return value or None


@frappe.whitelist()
def before_submit(doc: Document, method: str) -> None:
    for entry in doc.properties:
        utility_property = entry.utility_property
        if utility_property and entry.is_active:
            status = frappe.db.get_value("Utility Property", utility_property, "status")
            if status != "Available":
                frappe.throw(_("Utility Property {0} is not available. Current status: {1}. It must be available to submit the contract.").format(utility_property, status))
            
@frappe.whitelist()
def on_submit(doc: Document, method: str) -> None:
    for entry in doc.properties:
        utility_property = entry.utility_property
       
        if utility_property and entry.is_active:
            status = frappe.db.get_value("Utility Property", utility_property, "status")
            if doc.status == "Active" and status == ("Available" or "Reserved"):
                frappe.db.set_value("Utility Property", utility_property, "status", "Occupied")
            elif doc.status in ("Unsigned", "Inactive") and status in ("Available", "Reserved"):
                frappe.db.set_value("Utility Property", utility_property, "status", "Reserved")
            


@frappe.whitelist()
def on_cancel(doc: Document, method: str) -> None:
    for entry in doc.properties:
        utility_property = entry.utility_property
        if utility_property and entry.is_active:
            cancel_auto_repeats_for_property(utility_property)
            frappe.db.set_value("Utility Property", utility_property, "status", "Available")
            

@frappe.whitelist()
def on_update_after_submit(doc: Document, method: str) -> None:
    status_changed = doc.has_value_changed("status")
    current_status = doc.status

    for entry in doc.properties:
        utility_property = entry.utility_property
        if not utility_property:
            continue

        # Reactivating a row after submit is blocked in check_rows_unchanged

        if current_status == "Active" and entry.is_active:
            frappe.db.set_value("Utility Property", utility_property, "status", "Occupied")
            continue

        should_set_available = (
            (status_changed and entry.is_active) or
            (not status_changed and entry.has_value_changed("is_active") and not entry.is_active)
        )

        if should_set_available:
            cancel_auto_repeats_for_property(utility_property)
            frappe.db.set_value("Utility Property", utility_property, "status", "Available")



