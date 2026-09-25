import frappe
from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice
from erpnext.controllers.accounts_controller import AccountsController
from erpnext.controllers.taxes_and_totals import calculate_taxes_and_totals
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate

from ...utils.deferred_posting import (
	cancel_deferred_journal_entries,
	create_deferred_journal_entries,
	deferred_income_accounts,
	fill_posting_dates,
	validate_deferred_lines,
)
from ...utils.item_rate import get_rate_for_date
from ...utils.utils import sync_meter_readings

POSTING_DATE_FIELD = "custom_posting_date"
INVOICE_DOCTYPE = "Sales Invoice"
INVOICE_ITEM_DOCTYPE = "Sales Invoice Item"


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


def validate(doc: Document, method: str | None = None) -> None:
	"""Validate the meter readings and the deferred posting of the invoice."""
	sync_meter_readings(doc)
	fill_posting_dates(doc)
	validate_deferred_lines(doc)

	if doc.get("utility_service_request") and _is_item_price_approach():
		lock_utility_rates(doc)


def _is_item_price_approach() -> bool:
	"""Return whether rent is billed at the Item Price valid on the billing date.

	Rate locking and duplicate-period blocking only make sense under this
	approach - Auto Repeat has no Item Price schedule to resolve a rate from.
	"""
	return frappe.db.get_single_value("Utility Billing Settings", "rent_billing_approach") == "Item Price"


def lock_utility_rates(doc: Document) -> None:
	"""Re-resolve and lock each utility line's rate; block duplicate-period billing.

	The rate shown in the UI is only a convenience computed client side. This is
	the actual guarantee: whatever the client sent, the rate is overwritten here
	with the Item Price valid on the line's billing date. A line cannot bill the
	same item for a month already billed elsewhere in this same invoice, nor for
	a month a submitted invoice has already billed.

	Args:
		doc: Sales Invoice being validated.

	Raises:
		frappe.ValidationError: When no Item Price covers a line's item, customer
			and billing date, when another row of this same invoice already bills
			that item for the same month, or when a submitted invoice already
			billed it.
	"""
	seen_in_this_invoice: set[tuple[str, int, int]] = set()

	for row in doc.get("items") or []:
		if not row.item_code:
			continue

		billing_date = getdate(row.get(POSTING_DATE_FIELD) or doc.posting_date)

		key = (row.item_code, billing_date.month, billing_date.year)
		if key in seen_in_this_invoice:
			frappe.throw(
				_("Row #{0}: {1} is already billed for {2} by another row in this invoice.").format(
					row.idx, frappe.bold(row.item_code), billing_date.strftime("%B %Y")
				)
			)
		seen_in_this_invoice.add(key)

		rate = get_rate_for_date(
			row.item_code,
			billing_date,
			customer=doc.customer,
			price_list=doc.selling_price_list,
			uom=row.uom,
			qty=row.qty,
			conversion_factor=row.conversion_factor or 1,
			plc_conversion_rate=doc.plc_conversion_rate or 1,
			conversion_rate=doc.conversion_rate or 1,
		)

		if rate is None:
			frappe.throw(
				_("Row #{0}: No Item Price found for {1} valid on {2}.").format(
					row.idx, frappe.bold(row.item_code), billing_date
				)
			)

		row.price_list_rate = rate
		row.rate = rate
		row.amount = flt(rate) * flt(row.qty or 1)

		check_not_already_invoiced(doc, row, billing_date)


def check_not_already_invoiced(doc: Document, row, billing_date) -> None:
	"""Block a line billing a month already invoiced for the same item.

	Only submitted invoices count, so a draft can still be freely edited or
	discarded without permanently blocking that period.

	Args:
		doc: Sales Invoice being validated.
		row: Sales Invoice Item row being checked.
		billing_date: Resolved billing date of the row.

	Raises:
		frappe.ValidationError: When a submitted invoice already bills this item
			for the same month and year.
	"""
	invoice = frappe.qb.DocType(INVOICE_DOCTYPE)
	item = frappe.qb.DocType(INVOICE_ITEM_DOCTYPE)

	query = (
		frappe.qb.from_(item)
		.join(invoice)
		.on(item.parent == invoice.name)
		.select(invoice.name)
		.where(invoice.docstatus == 1)
		.where(invoice.name != (doc.name or ""))
		.where(item.item_code == row.item_code)
		.where(frappe.qb.terms.Function("MONTH", item[POSTING_DATE_FIELD]) == billing_date.month)
		.where(frappe.qb.terms.Function("YEAR", item[POSTING_DATE_FIELD]) == billing_date.year)
		.limit(1)
	)

	existing = query.run()
	if existing:
		frappe.throw(
			_("Row #{0}: {1} was already invoiced for {2} on {3}.").format(
				row.idx,
				frappe.bold(row.item_code),
				billing_date.strftime("%B %Y"),
				frappe.bold(existing[0][0]),
			)
		)


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