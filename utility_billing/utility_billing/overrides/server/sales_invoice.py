from frappe.model.document import Document
import frappe
from erpnext.controllers.taxes_and_totals import calculate_taxes_and_totals
from erpnext.controllers.accounts_controller import AccountsController
from frappe.model.mapper import get_mapped_doc


def before_validate(doc: Document, method: str) -> None:
    """Intercepts submit event for document"""
    AccountsController.append_taxes_from_item_tax_template(doc)
    calculate_taxes_and_totals(doc)
    unique_sales_orders = {item.sales_order for item in doc.items if item.sales_order}
    for sales_order in unique_sales_orders:
        map_sales_order_meter_readings_to_invoice(sales_order, doc, True)



def map_sales_order_meter_readings_to_invoice(source_name, target_doc, ignore_permissions):
    """Map Sales Order to Sales Invoice, including meter readings."""
    return get_mapped_doc(
        "Sales Order",
        source_name,
        {
           "Sales Order": {
                "doctype": "Sales Invoice",
                "field_map": {
                    "party_account_currency": "party_account_currency",
                    "payment_terms_template": "payment_terms_template",
                },
                "field_no_map": ["payment_terms_template"],
                "validation": {"docstatus": ["=", 1]},
            },
            "Sales Order Meter Reading": { 
                "doctype": "Sales Invoice Meter Reading",
                "add_if_empty": True,
            }
        },
        target_doc,
        ignore_permissions=ignore_permissions,
    )

