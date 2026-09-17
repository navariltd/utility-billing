import frappe
from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice
from erpnext.controllers.accounts_controller import AccountsController
from erpnext.controllers.taxes_and_totals import calculate_taxes_and_totals
from frappe.model.document import Document
from ...utils.deferred_posting import (
	cancel_deferred_journal_entries,
	create_deferred_journal_entries,
	deferred_income_accounts,
	fill_posting_dates,
	validate_deferred_lines,
)
from ...utils.utils import (
	sync_meter_readings,
)


class UtilityBillingSalesInvoice(SalesInvoice):
	"""Sales Invoice applying the deferred posting of Utility Billing.

	Deferred lines credit the deferred account of their company instead of their
	income account when the invoice is posted. The revenue reaches the income
	account through a Journal Entry dated the Deferred Posting Date of the line.
	"""

	def get_gl_entries(self, inventory_account_map=None):
		"""Build the GL entries, crediting deferred accounts for deferred lines."""
		with deferred_income_accounts(self):
			return super().get_gl_entries(inventory_account_map)


def validate(doc: Document, method: str) -> None:
	"""Validate the meter readings and the deferred posting of the invoice."""
	sync_meter_readings(doc)
	fill_posting_dates(doc)
	validate_deferred_lines(doc)

def before_validate(doc: Document, method: str) -> None:
    """Intercepts submit event for document"""
    if not doc.taxes:
        AccountsController.append_taxes_from_item_tax_template(doc)
        calculate_taxes_and_totals(doc)
    unique_sales_orders = {
        item.sales_order
        for item in frappe.get_all(
            "Sales Invoice Item",
            filters={"parent": doc.name, "sales_order": ["is", "set"]},
            fields=["sales_order"],
        )
    }   

    for sales_order in unique_sales_orders:
        map_sales_order_meter_readings_to_invoice(sales_order, doc)


def map_sales_order_meter_readings_to_invoice(sales_order_name, target_doc):
    """Map all fields from Sales Order Meter Reading to Sales Invoice Meter Reading."""
    sales_order = frappe.get_doc("Sales Order", sales_order_name)
    meter_readings = sales_order.get("meter_readings")
    target_doc.set("meter_readings", [])
    if sales_order.utility_property:
        target_doc.utility_property = sales_order.utility_property
    if sales_order.utility_service_request:
        target_doc.utility_service_request = sales_order.utility_service_request

    for reading in meter_readings:
        new_reading_data = reading.as_dict()
        new_reading_data.pop("name", None)
        new_reading = target_doc.append("meter_readings", new_reading_data)
        new_reading.parent = target_doc.name

def on_submit(doc: Document, method: str) -> None:
	"""Recognise the deferred revenue of the invoice on its deferred dates."""
	create_deferred_journal_entries(doc)


def on_cancel(doc: Document, method: str) -> None:
	"""Cancel the journal entries that recognised the deferred revenue."""
	cancel_deferred_journal_entries(doc)
