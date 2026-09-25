import frappe
from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice
from erpnext.controllers.accounts_controller import AccountsController
from erpnext.controllers.taxes_and_totals import calculate_taxes_and_totals
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, fmt_money, getdate

from ...utils.deferred_posting import (
	cancel_deferred_journal_entries,
	create_deferred_journal_entries,
	deferred_income_accounts,
	fill_posting_dates,
	validate_deferred_lines,
)
from ...utils.item_price_scope import is_item_price_approach
from ...utils.item_rate import get_rate_for_date
from ...utils.utility_item_classifier import (
	MATCH_MULTIPLE,
	PRIMARY,
	USR_DOCTYPE,
	get_request_lines,
	get_utility_items,
	match_error_message,
	match_requests,
)
from ...utils.utils import sync_meter_readings

POSTING_DATE_FIELD = "custom_posting_date"
INVOICE_DOCTYPE = "Sales Invoice"
INVOICE_ITEM_DOCTYPE = "Sales Invoice Item"
REQUEST_FIELD = "utility_service_request"


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
	"""Validate the meter readings, the deferred posting and the utility rates of the invoice."""
	sync_meter_readings(doc)
	fill_posting_dates(doc)
	validate_deferred_lines(doc)

	if is_item_price_approach():
		govern_utility_lines(doc)


def govern_utility_lines(doc: Document) -> None:
	"""Link the invoice to its Utility Service Request and enforce its utility rates.

	Utility lines must all belong to one submitted Utility Service Request of the
	customer, which is linked when it is the only one. Primary lines are billed at
	the Item Price valid on their billing date, secondary lines at the rate on the
	request. No utility line may bill a month already billed, in this invoice or
	in a submitted one. Non utility items, lines priced from a Meter Reading and
	return invoices are left alone.

	An invoice that no longer bills any utility item has nothing left to govern,
	so a request linked earlier is cleared rather than left pointing at items the
	invoice no longer bills.

	Args:
		doc: Sales Invoice being validated.

	Raises:
		frappe.ValidationError: When the utility lines cannot be matched to one
			request, a rate does not follow its source, or a month is billed twice.
	"""
	if doc.get("is_return"):
		return

	rows = get_governed_rows(doc)
	if not rows:
		if doc.get(REQUEST_FIELD):
			doc.set(REQUEST_FIELD, None)
		return

	service_request = link_service_request(doc, [row.item_code for row in rows])
	lines = get_request_lines(service_request)
	seen_in_this_invoice: set[tuple[str, int, int]] = set()

	for row in rows:
		line = lines[row.item_code]
		billing_date = getdate(row.get(POSTING_DATE_FIELD) or doc.posting_date)
		check_not_billed_twice_in_invoice(row, billing_date, seen_in_this_invoice)

		if line.role == PRIMARY:
			apply_schedule_rate(doc, row, billing_date)
			check_not_already_invoiced(doc, row, billing_date)
		else:
			check_request_rate(doc, row, line, service_request)
			check_not_already_invoiced(doc, row, billing_date, service_request=service_request)


def get_governed_rows(doc: Document) -> list:
	"""Return the lines billing a utility item, except those priced from a Meter Reading."""
	rows = [row for row in doc.get("items") or [] if row.item_code and not row.get("meter_reading")]
	utility_items = get_utility_items(row.item_code for row in rows)

	return [row for row in rows if row.item_code in utility_items]


def link_service_request(doc: Document, item_codes: list[str]) -> str:
	"""Return the Utility Service Request governing the utility lines.

	The request is linked when it is the only one covering every utility line.

	Args:
		doc: Sales Invoice being validated.
		item_codes: Utility items billed by the invoice.

	Returns:
		The governing ``Utility Service Request`` name.

	Raises:
		frappe.ValidationError: When no single request covers every utility
			line, the linked request does not, several do and none is chosen, or
			the request is in another currency.
	"""
	match = match_requests(doc.customer, item_codes)

	message = match_error_message(match, doc.customer)
	if message:
		frappe.throw(message, title=_("Utility Service Request required"))

	service_request = doc.get(REQUEST_FIELD)

	if service_request and service_request not in match.candidates:
		frappe.throw(
			_(
				"Utility Service Request {0} does not cover every utility item on this invoice. "
				"Choose one of: {1}."
			).format(frappe.bold(service_request), ", ".join(match.candidates))
		)

	if not service_request:
		if match.status == MATCH_MULTIPLE:
			frappe.throw(
				_(
					"Several Utility Service Requests of {0} cover the utility items on this "
					"invoice. Select one in the Utility Service Request field: {1}."
				).format(frappe.bold(doc.customer), ", ".join(match.candidates))
			)

		service_request = match.candidates[0]
		doc.set(REQUEST_FIELD, service_request)

	check_request_currency(doc, service_request)

	return service_request


def check_request_currency(doc: Document, service_request: str) -> None:
	"""Block an invoice billed in another currency than its Utility Service Request."""
	currency = frappe.db.get_value(USR_DOCTYPE, service_request, "currency")

	if currency and currency != doc.currency:
		frappe.throw(
			_(
				"Utility Service Request {0} is in {1} but this invoice is in {2}. Utility "
				"lines can only be billed in the request's currency."
			).format(frappe.bold(service_request), currency, doc.currency)
		)


def check_not_billed_twice_in_invoice(row, billing_date, seen: set) -> None:
	"""Block a line billing an item for a month another line of the invoice bills."""
	key = (row.item_code, billing_date.month, billing_date.year)

	if key in seen:
		frappe.throw(
			_("Row #{0}: {1} is already billed for {2} by another row in this invoice.").format(
				row.idx, frappe.bold(row.item_code), billing_date.strftime("%B %Y")
			)
		)

	seen.add(key)


def apply_schedule_rate(doc: Document, row, billing_date) -> None:
	"""Lock a primary line to the Item Price valid on its billing date.

	Whatever the client sent, the rate is overwritten here.

	Raises:
		frappe.ValidationError: When no Item Price covers the item, the customer
			and the billing date.
	"""
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


def check_request_rate(doc: Document, row, line, service_request: str) -> None:
	"""Block a secondary line whose rate is not the rate on its Utility Service Request.

	Raises:
		frappe.ValidationError: When the saved rate differs from the request row.
	"""
	precision = row.precision("rate")

	if flt(row.rate, precision) != flt(line.rate, precision):
		frappe.throw(
			_(
				"Row #{0}: The rate of {1} must be {2}, the rate agreed on Utility Service "
				"Request {3}."
			).format(
				row.idx,
				frappe.bold(row.item_code),
				frappe.bold(fmt_money(line.rate, currency=doc.currency)),
				frappe.bold(service_request),
			)
		)


def check_not_already_invoiced(
	doc: Document, row, billing_date, service_request: str | None = None
) -> None:
	"""Block a line billing a month already invoiced for the same item.

	Only submitted invoices count, so a draft can still be freely edited or
	discarded without permanently blocking that period. Primary items belong to
	a single property, so the item alone scopes the check. Secondary items are
	often shared by many customers, so their check is scoped to the request too.

	Args:
		doc: Sales Invoice being validated.
		row: Sales Invoice Item row being checked.
		billing_date: Resolved billing date of the row.
		service_request: Request the check is scoped to, for secondary items.

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

	if service_request:
		query = query.where(invoice[REQUEST_FIELD] == service_request)

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