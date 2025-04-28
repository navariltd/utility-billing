import frappe
from frappe.query_builder import DocType

@frappe.whitelist()
def cancel_auto_repeats_for_property(property_name: str) -> None:
    SalesInvoice = DocType("Sales Invoice")
    SalesInvoiceItem = DocType("Sales Invoice Item")
    AutoRepeat = DocType("Auto Repeat")

    invoice_query = (
        frappe.qb.from_(SalesInvoice)
        .left_join(SalesInvoiceItem)
        .on(SalesInvoice.name == SalesInvoiceItem.parent)
        .select(SalesInvoice.name)
        .where(
            (SalesInvoice.utility_property == property_name)
            | (SalesInvoiceItem.utility_property == property_name)
        )
        .distinct()
    )
    invoice_names = [row[0] for row in invoice_query.run()]
    
    if not invoice_names:
        return

    auto_repeat_query = (
        frappe.qb.from_(AutoRepeat)
        .select(AutoRepeat.name, AutoRepeat.reference_document)
        .where(
            (AutoRepeat.reference_doctype == "Sales Invoice")
            & (AutoRepeat.reference_document.isin(invoice_names))
        )
    )
    auto_repeats = auto_repeat_query.run()
    for auto_repeat in auto_repeats:
        auto_repeat_name = auto_repeat[0]
        auto_repeat_doc = frappe.get_doc("Auto Repeat", auto_repeat_name)
        auto_repeat_doc.disabled = 1
        auto_repeat_doc.save()
