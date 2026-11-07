import frappe
from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice
from erpnext.controllers.accounts_controller import AccountsController
from erpnext.controllers.taxes_and_totals import calculate_taxes_and_totals
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, fmt_money, getdate

from ...utils.cost_center import (
	default_cost_center,
	request_row_property,
	requested_properties,
	resolve_primary_cost_center,
	service_item_owners,
)
from ...utils.deferred_posting import (
	cancel_deferred_journal_entries,
	create_deferred_journal_entries,
	deferred_income_accounts,
	fill_posting_dates,
	validate_deferred_lines,
)
from ...utils.item_price_scope import is_item_price_approach
from ...utils.item_rate import get_rate_for_date
from ...utils.release import owns
from ...utils.line_request import (
	ORDINARY,
	RESOLVED,
	billing_date as line_billing_date,
	get_governed_rows,
	line_request,
	move_header_to_lines,
	request_of_line,
	resolve_lines,
	uses_header_path,
)
from ...utils.utility_item_classifier import (
	MATCH_MULTIPLE,
	PRIMARY,
	USR_DOCTYPE,
	get_lease_periods,
	get_request_lines,
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

	def on_recurring(self, reference_doc, auto_repeat_doc):
		"""Clear the Deferred Posting Dates copied from the Auto Repeat reference.

		Auto Repeat copies every line of the reference invoice, dates included,
		and only moves the invoice Posting Date. Clearing the line dates lets
		``fill_posting_dates`` derive them from the new Posting Date on validate,
		instead of the copy billing the months of the reference again.

		A copy of an invoice carrying its requests on its lines also drops the
		request of each line with a property: it is found again from the
		property and the new date, which may fall in another request's lease.
		A request picked by hand on a line without a property is kept, and
		checked again on validate. Under Item Price its rent lines also drop
		the rate of the reference, so they bill the price of their new date
		(see ``clear_rent_rates``). A copy linked through its header is left as
		it is.
		"""
		super().on_recurring(reference_doc, auto_repeat_doc)

		for row in self.get("items") or []:
			row.set(POSTING_DATE_FIELD, None)
			if not self.get(REQUEST_FIELD) and row.get("utility_property") and not row.get("meter_reading"):
				row.set(REQUEST_FIELD, None)

		if not self.get(REQUEST_FIELD) and is_item_price_approach():
			clear_rent_rates(self)


RENT_RATE_FIELDS = ("price_list_rate", "rate", "discount_percentage", "discount_amount", "margin_rate_or_amount")


def clear_rent_rates(doc: Document) -> None:
	"""Clear the rates of the rent lines of an Auto Repeat copy.

	The copy keeps the reference's rates; on a new date with another Item
	Price, ERPNext would keep the old rate as a discount or a margin, which
	``check_schedule_rate`` refuses. Cleared, the line takes the price of its
	new date in ``prefill_line_rates``. A rent line is one billing the service
	item of its property; meter lines are left alone.
	"""
	rows = [row for row in doc.get("items") or [] if row.get("utility_property") and not row.get("meter_reading")]
	owners = service_item_owners(list({row.utility_property for row in rows}))
	for row in rows:
		if row.utility_property in owners.get(row.item_code, ()):
			for fieldname in RENT_RATE_FIELDS:
				row.set(fieldname, 0)
			row.set("margin_type", None)


def validate(doc: Document, method: str | None = None) -> None:
	"""Validate the meter readings, the deferred posting and the utility rates of the invoice."""
	sync_meter_readings(doc)
	fill_posting_dates(doc)
	validate_deferred_lines(doc)

	governed = govern_utility_lines(doc) if is_item_price_approach() else []
	# After linking, so a request linked on this save already gives its lines their cost center.
	fill_request_line_dimensions(doc)
	if governed and not uses_header_path(doc):
		check_utility_cost_centers(doc, governed)

	# Once per request on the invoice: the lines' own, else the header's
	for service_request, entries in governed_by_request(doc, governed).items():
		contract = check_service_request_contract(doc, service_request)
		if contract:
			check_within_contract(contract, entries)


def governed_by_request(doc: Document, governed: list[frappe._dict]) -> dict[str, list[frappe._dict]]:
	"""Group the governed lines by their request; without any, the header's request alone."""
	groups: dict[str, list[frappe._dict]] = {}
	for entry in governed:
		service_request = entry.get("service_request") or doc.get(REQUEST_FIELD)
		if service_request:
			groups.setdefault(service_request, []).append(entry)

	if not groups and doc.get(REQUEST_FIELD):
		groups[doc.get(REQUEST_FIELD)] = []

	return groups


def govern_utility_lines(doc: Document) -> list[frappe._dict]:
	"""Give each utility line its Utility Service Request and enforce its utility rates.

	Each governed line gets its own request (see ``line_request``), so one
	invoice may bill lines of several requests of its customer. A request on
	the header of a draft is moved onto its governed lines without one and the
	header is cleared, so the header and the lines never both apply. Lines of
	other items carry no request. Drafts generated by Auto Repeat from an
	invoice linked through its header keep the header and are governed by
	``govern_header_lines``, as before. A service line without a property is
	an ordinary line: no request, no property, its own cost center.

	Then, per request, every utility line must bill a date within its lease,
	primary lines are billed at the Item Price valid on their billing date,
	secondary lines at the rate on the request, and no line may bill a month
	already billed. Lines priced from a Meter Reading and return invoices are
	left alone.

	Returns:
		One entry per governed line with its ``row``, ``billing_date``, the
		``utility_property`` it bills (``None`` for secondary lines) and its
		``service_request``.

	Raises:
		frappe.ValidationError: When a line has no request, a line bills outside
			its lease, a rate does not follow its request, or a month is billed
			twice.
	"""
	if doc.get("is_return"):
		return []

	if uses_header_path(doc):
		return govern_header_lines(doc)

	rows = get_governed_rows(doc)
	resolutions = {}
	if rows:
		move_header_to_lines(doc, rows)
		resolutions = resolve_lines(doc, rows)
		# A service line without a property is an ordinary line
		rows = [row for row in rows if resolutions[row.name or str(row.idx)].status != ORDINARY]

	clear_other_lines(doc, rows)
	if not rows:
		if doc.get(REQUEST_FIELD):
			doc.set(REQUEST_FIELD, None)
		return []

	for row in rows:
		result = resolutions[row.name or str(row.idx)]
		if result.status != RESOLVED:
			frappe.throw(result.message, title=_("Utility Service Request required"))

		row.set(REQUEST_FIELD, result.service_request)
		if result.utility_property:
			row.utility_property = result.utility_property

	requests: dict[str, tuple] = {}
	seen_in_this_invoice: set[tuple] = set()
	governed = []

	for row in rows:
		service_request = row.get(REQUEST_FIELD)
		if service_request not in requests:
			check_request_currency(doc, service_request)
			lines = get_request_lines(service_request)
			requests[service_request] = (lines, get_lease_periods(service_request, lines))

		lines, leases = requests[service_request]
		line = lines[row.item_code]
		lease = leases[row.item_code]
		billing_date = line_billing_date(doc, row)
		check_within_lease(row, billing_date, lease)

		if line.role == PRIMARY:
			check_not_billed_twice_in_invoice(row, billing_date, seen_in_this_invoice)
			# Set by ``prefill_line_rates`` before the totals; only checked here, never overwritten
			check_schedule_rate(doc, row, billing_date, service_request)
			check_not_already_invoiced(doc, row, billing_date)
		else:
			# A secondary item may be billed once a month on each of the requests it is on.
			# Its rate is the request row's when the line had none, and stays editable.
			check_not_billed_twice_in_invoice(row, billing_date, seen_in_this_invoice, service_request)
			check_not_already_invoiced(doc, row, billing_date, service_request=service_request)

		governed.append(
			frappe._dict(
				row=row,
				billing_date=billing_date,
				utility_property=lease.utility_property,
				service_request=service_request,
			)
		)

	return governed


def clear_other_lines(doc: Document, governed_rows: list) -> None:
	"""Clear the request and the property of lines billing an item that needs neither.

	An ordinary item bills no property; one copied onto its line (ERPNext copies
	the first row's accounting dimensions into a new row) is cleared, so its
	cost center stays ERPNext's. Meter lines are left alone.
	"""
	governed = {id(row) for row in governed_rows}
	for row in doc.get("items") or []:
		if id(row) in governed or row.get("meter_reading"):
			continue
		if row.get(REQUEST_FIELD):
			row.set(REQUEST_FIELD, None)
		if row.get("utility_property"):
			row.set("utility_property", None)


def govern_header_lines(doc: Document) -> list[frappe._dict]:
	"""Link the invoice to its Utility Service Request and enforce its utility rates.

	The header path, unchanged from before requests moved to the lines. Only
	drafts generated by Auto Repeat from an invoice linked through its header
	take it.

	Utility lines must all belong to one submitted Utility Service Request of the
	customer, which is linked when it is the only one. Every utility line must bill
	a date within its lease. Primary lines are billed at the Item Price valid on
	their billing date, secondary lines at the rate on the request. No utility line
	may bill a month already billed, in this invoice or in a submitted one. Non
	utility items, lines priced from a Meter Reading and return invoices are left
	alone.

	An invoice that no longer bills any utility item has nothing left to govern,
	so a request linked earlier is cleared rather than left pointing at items the
	invoice no longer bills.

	Args:
		doc: Sales Invoice being validated.

	Returns:
		One entry per governed line with its ``row``, ``billing_date`` and the
		``utility_property`` it bills (``None`` for secondary lines).

	Raises:
		frappe.ValidationError: When the utility lines cannot be matched to one
			request, a line bills outside its lease, a rate does not follow its
			source, or a month is billed twice.
	"""
	if doc.get("is_return"):
		return []

	rows = get_governed_rows(doc)
	if not rows:
		if doc.get(REQUEST_FIELD):
			doc.set(REQUEST_FIELD, None)
		return []

	billing_dates: dict[str, list] = {}
	for row in rows:
		billing_dates.setdefault(row.item_code, []).append(
			getdate(row.get(POSTING_DATE_FIELD) or doc.posting_date)
		)

	service_request = link_service_request(doc, [row.item_code for row in rows], billing_dates)
	lines = get_request_lines(service_request)
	leases = get_lease_periods(service_request, lines)
	seen_in_this_invoice: set[tuple[str, int, int]] = set()
	governed = []

	for row in rows:
		line = lines[row.item_code]
		lease = leases[row.item_code]
		billing_date = getdate(row.get(POSTING_DATE_FIELD) or doc.posting_date)
		check_within_lease(row, billing_date, lease)
		check_not_billed_twice_in_invoice(row, billing_date, seen_in_this_invoice)

		if line.role == PRIMARY:
			apply_schedule_rate(doc, row, billing_date, service_request)
			check_not_already_invoiced(doc, row, billing_date)
		else:
			check_request_rate(doc, row, line, service_request)
			check_not_already_invoiced(doc, row, billing_date, service_request=service_request)

		governed.append(
			frappe._dict(
				row=row, billing_date=billing_date, utility_property=lease.utility_property
			)
		)

	return governed


def check_within_lease(row, billing_date, lease) -> None:
	"""Block a line billing a date outside the lease it belongs to.

	Always applies to governed lines, whether or not a Contract exists: Item
	Prices alone cannot guarantee it, since prices without a customer or end
	date, prices left from a longer lease and secondary items all resolve a
	rate outside the lease. Open ended leases enforce no end.

	Args:
		row: Sales Invoice Item row being checked.
		billing_date: Resolved billing date of the row.
		lease: Entry of ``get_lease_periods`` for the row's item.

	Raises:
		frappe.ValidationError: Naming the line, the billing date and the boundary.
	"""
	if lease.start and billing_date < getdate(lease.start):
		frappe.throw(
			_("Row #{0}: {1} is billed for {2}, before the lease of {3} starts on {4}.").format(
				row.idx, frappe.bold(row.item_code), billing_date, lease.label, getdate(lease.start)
			)
		)

	if lease.end and billing_date > getdate(lease.end):
		frappe.throw(
			_("Row #{0}: {1} is billed for {2}, after the lease of {3} ended on {4}.").format(
				row.idx, frappe.bold(row.item_code), billing_date, lease.label, getdate(lease.end)
			)
		)


def check_service_request_contract(doc: Document, service_request: str | None = None) -> str | None:
	"""Block invoicing a Utility Service Request without the Contract the settings require.

	With Require Contract Before Sales Invoice Creation on, the request needs a
	submitted Contract - and a signed one when Require Signed Contract is on too.
	A Contract that released its properties still satisfies it: under Item Price
	``check_within_contract`` then refuses each line billing a day after its
	row's Released On.

	Known limitation: this also applies to invoices Auto Repeat generates, so a
	request without the required Contract makes that scheduled generation fail
	with this error instead of warning anyone up front.

	Args:
		doc: Sales Invoice being validated.
		service_request: Request checked; the invoice header's when not given.

	Returns:
		The name of the Contract satisfying the requirement, or ``None`` when no
		Contract is required.

	Raises:
		frappe.ValidationError: When the required Contract does not exist.
	"""
	service_request = service_request or doc.get(REQUEST_FIELD)
	if doc.get("is_return") or not service_request:
		return None

	settings = frappe.get_cached_doc("Utility Billing Settings")
	if not settings.require_contract_before_sales_invoice_creation:
		return None

	filters = {"utility_service_request": service_request, "docstatus": 1}
	if settings.require_signed_contract:
		filters["is_signed"] = 1

	contracts = frappe.get_all("Contract", filters=filters, pluck="name", order_by="creation desc")
	if contracts:
		# A Contract that released its properties still covers the days up to each
		# row's Released On: ``check_within_contract`` compares the billing dates.
		return contracts[0]

	if settings.require_signed_contract:
		frappe.throw(
			_(
				"Utility Service Request {0} has no signed, submitted Contract. Sign and "
				"submit its Contract before invoicing it."
			).format(frappe.bold(service_request))
		)

	frappe.throw(
		_(
			"Utility Service Request {0} has no submitted Contract. Submit its Contract "
			"before invoicing it."
		).format(frappe.bold(service_request))
	)


def check_within_contract(contract_name: str, governed: list[frappe._dict]) -> None:
	"""Block a line billing a date the Contract does not cover.

	Deliberately independent of the lease check: the Contract is read on its
	own, so a request edited after its Contract was made surfaces as a mismatch
	instead of one source silently winning. A line's coverage is the Contract
	row of its property, falling back to the Contract's own dates; a secondary
	line has no property, so it uses the Contract's own dates. Blank dates are
	open ended.

	The Contract is read fresh on every call. Its rows are locked to what
	``create_contract`` copied from the request, so they may differ from the
	request's current rows.

	Args:
		contract_name: Contract satisfying the requirement.
		governed: Result of ``govern_utility_lines``.

	Raises:
		frappe.ValidationError: Naming the line, the billing date, the Contract
			and the boundary.
	"""
	if not governed:
		return

	contract = frappe.get_doc("Contract", contract_name)
	rows_by_property = {
		row.utility_property: row for row in contract.get("properties") or [] if row.utility_property
	}

	for line in governed:
		contract_row = rows_by_property.get(line.utility_property)
		if contract_row and not contract_row.is_active:
			check_before_release(line, contract, contract_row)

		start = (contract_row and contract_row.start_date) or contract.start_date
		end = (contract_row and contract_row.end_date) or contract.end_date
		coverage = (
			_("property {0} on Contract {1}").format(line.utility_property, contract.name)
			if contract_row
			else _("Contract {0}").format(contract.name)
		)

		if start and line.billing_date < getdate(start):
			frappe.throw(
				_("Row #{0}: {1} is billed for {2}, before {3} starts on {4}.").format(
					line.row.idx,
					frappe.bold(line.row.item_code),
					line.billing_date,
					coverage,
					getdate(start),
				)
			)

		if end and line.billing_date > getdate(end):
			frappe.throw(
				_("Row #{0}: {1} is billed for {2}, after {3} ended on {4}.").format(
					line.row.idx,
					frappe.bold(line.row.item_code),
					line.billing_date,
					coverage,
					getdate(end),
				)
			)


def check_before_release(line, contract, contract_row) -> None:
	"""Block a line billing a day after its property was released on the Contract.

	The release day is inclusive; a released row without Released On covers nothing.
	"""
	start = contract_row.start_date or contract.start_date
	end = contract_row.end_date or contract.end_date
	released_on = contract_row.get("released_on")
	if owns(start, end, line.billing_date, True, released_on):
		return

	if released_on:
		frappe.throw(
			_("Row #{0}: {1} is billed for {2}, after property {3} was released on Contract {4} on {5}.").format(
				line.row.idx,
				frappe.bold(line.row.item_code),
				line.billing_date,
				line.utility_property,
				contract.name,
				getdate(released_on),
			)
		)

	frappe.throw(
		_("Row #{0}: {1} is billed for {2}, but property {3} was released on Contract {4} without a Released On date.").format(
			line.row.idx, frappe.bold(line.row.item_code), line.billing_date, line.utility_property, contract.name
		)
	)


def link_service_request(
	doc: Document, item_codes: list[str], billing_dates: dict | None = None
) -> str:
	"""Return the Utility Service Request governing the utility lines.

	The request is linked when it is the only one covering every utility line,
	or the only one of several whose leases cover every billing date.

	Args:
		doc: Sales Invoice being validated.
		item_codes: Utility items billed by the invoice.
		billing_dates: Mapping of item code to the dates it is billed for.

	Returns:
		The governing ``Utility Service Request`` name.

	Raises:
		frappe.ValidationError: When no single request covers every utility
			line, the linked request does not, several do and none is chosen, or
			the request is in another currency.
	"""
	match = match_requests(doc.customer, item_codes, billing_dates)

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


def check_not_billed_twice_in_invoice(row, billing_date, seen: set, scope: str | None = None) -> None:
	"""Block a line billing an item for a month another line of the invoice bills.

	``scope`` narrows the check to one request, for a secondary item billed on
	the lines of several requests.
	"""
	key = (row.item_code, billing_date.month, billing_date.year, scope)

	if key in seen:
		frappe.throw(
			_("Row #{0}: {1} is already billed for {2} by another row in this invoice.").format(
				row.idx, frappe.bold(row.item_code), billing_date.strftime("%B %Y")
			)
		)

	seen.add(key)


def apply_schedule_rate(doc: Document, row, billing_date, service_request: str) -> None:
	"""Lock a primary line to the Item Price its request owns on its billing date.

	Whatever the client sent, the rate is overwritten here. Prices of another
	request, or linked to none, are never used.

	Raises:
		frappe.ValidationError: When no Item Price covers the item, the customer
			and the billing date.
	"""
	rate = schedule_rate(doc, row, billing_date, service_request)

	if rate is None:
		frappe.throw(
			_("Row #{0}: No Item Price of Utility Service Request {1} found for {2} valid on {3}.").format(
				row.idx, frappe.bold(service_request), frappe.bold(row.item_code), billing_date
			)
		)

	row.price_list_rate = rate
	row.rate = rate
	row.amount = flt(rate) * flt(row.qty or 1)


def schedule_rate(doc: Document, row, billing_date, service_request: str) -> float | None:
	"""Return the Item Price a rent line's request owns on its billing date, if any."""
	return get_rate_for_date(
		row.item_code,
		billing_date,
		customer=doc.customer,
		price_list=doc.selling_price_list,
		uom=row.uom,
		qty=row.qty,
		conversion_factor=row.conversion_factor or 1,
		plc_conversion_rate=doc.plc_conversion_rate or 1,
		conversion_rate=doc.conversion_rate or 1,
		service_request=service_request,
	)


def check_schedule_rate(doc: Document, row, billing_date, service_request: str) -> None:
	"""Block a rent line not billed at its request's Item Price on its billing date.

	Rent is locked to the schedule: ``prefill_line_rates`` sets the price list
	rate before ERPNext computes the totals, and the rate ERPNext keeps must be
	that price, so a typed rate, a discount, a margin or a pricing rule is
	refused rather than overwritten, and the totals always agree with the line.

	Raises:
		frappe.ValidationError: When no Item Price covers the line, or its price
			list rate or its rate differs.
	"""
	rate = schedule_rate(doc, row, billing_date, service_request)
	if rate is None:
		frappe.throw(
			_("Row #{0}: No Item Price of Utility Service Request {1} found for {2} valid on {3}.").format(
				row.idx, frappe.bold(service_request), frappe.bold(row.item_code), billing_date
			)
		)

	precision = row.precision("price_list_rate")
	if flt(row.price_list_rate, precision) != flt(rate, precision):
		frappe.throw(
			_("Row #{0}: The price list rate of {1} must be {2}, the Item Price of Utility Service Request {3} valid on {4}.").format(
				row.idx,
				frappe.bold(row.item_code),
				frappe.bold(fmt_money(rate, currency=doc.currency)),
				frappe.bold(service_request),
				billing_date,
			)
		)

	precision = row.precision("rate")
	if flt(row.rate, precision) != flt(rate, precision):
		frappe.throw(
			_(
				"Row #{0}: {1} is rent and bills {2}, the Item Price of Utility Service Request {3} valid on {4}, "
				"not {5}. Remove the discount, margin or pricing rule on the line, or change the Item Price."
			).format(
				row.idx,
				frappe.bold(row.item_code),
				frappe.bold(fmt_money(rate, currency=doc.currency)),
				frappe.bold(service_request),
				billing_date,
				frappe.bold(fmt_money(row.rate, currency=doc.currency)),
			),
			title=_("Rent rate is locked"),
		)


def prefill_line_rates(doc: Document) -> None:
	"""Set the rates of utility lines before ERPNext computes the totals, under Item Price.

	Runs in before_validate. A rent line takes its schedule Item Price as its
	price list rate, and ERPNext derives the rate, the amounts and the totals
	from it as usual; nothing is written after ERPNext's calculation, and
	``check_schedule_rate`` refuses a rate ERPNext kept that is not the price. A service
	line without a rate takes its request row's rate; a rate the user set is kept. Lines without a request
	are left to ``validate``, which says why. A line without a property takes
	the one property of its cost center, when it has exactly one.

	Drafts keeping their header request, return invoices and invoices inserted
	without validation are left as before.
	"""
	if (
		not is_item_price_approach()
		or doc.docstatus != 0
		or doc.get("is_return")
		or doc.flags.ignore_validate
		or uses_header_path(doc)
		or not doc.get("customer")
	):
		return

	rows = get_governed_rows(doc)
	if not rows:
		return

	fill_property_from_cost_center(rows)
	results = resolve_lines(doc, rows)
	request_lines: dict[str, dict] = {}
	for row in rows:
		result = results[row.name or str(row.idx)]
		if result.status != RESOLVED:
			continue

		if result.service_request not in request_lines:
			request_lines[result.service_request] = get_request_lines(result.service_request)
		line = request_lines[result.service_request].get(row.item_code)
		if not line:
			continue

		if line.role == PRIMARY:
			rate = schedule_rate(doc, row, line_billing_date(doc, row), result.service_request)
			if rate is not None:
				row.price_list_rate = rate
		elif not flt(row.rate) and not flt(row.price_list_rate):
			row.price_list_rate = line.rate
			row.rate = line.rate


def fill_property_from_cost_center(rows) -> None:
	"""Give a line without a property the property of its cost center, when only one property has it."""
	for row in rows:
		if row.get("utility_property") or not row.get("cost_center"):
			continue

		properties = frappe.get_all("Utility Property", filters={"cost_center": row.cost_center}, pluck="name", limit=2)
		if len(properties) == 1:
			row.utility_property = properties[0]


def check_utility_cost_centers(doc: Document, governed: list[frappe._dict]) -> None:
	"""Block a utility line left without a cost center."""
	for entry in governed:
		if not entry.row.get("cost_center"):
			frappe.throw(
				_("Row #{0}: {1} needs a cost center. Pick its property, or its cost center.").format(
					entry.row.idx, frappe.bold(entry.row.item_code)
				)
			)


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
		# A submitted line's own request, else its invoice's (an invoice from before lines had one)
		query = query.where(request_of_line(item, invoice) == service_request)

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
	# Before ERPNext computes the totals, so they agree with the rates
	prefill_line_rates(doc)
	# Also here, as invoices inserted with ``ignore_validate`` never reach ``validate``.
	fill_request_line_dimensions(doc)
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


def fill_request_line_dimensions(doc: Document) -> None:
	"""Give the lines that came from a request the cost center of their request.

	Each line is filled from its own request, else the invoice header's (an
	invoice from before lines had one, or a draft Auto Repeat generated from
	it), so lines of several requests each take their own. A line of an item
	that needs no request keeps ERPNext's cost center.

	Only under the Item Price approach; under Auto Repeat invoice lines are left
	exactly as they are. A line came from the request when its item is on the
	request's item rows; meter lines, lines of items the request does not list
	and return invoices are left to ERPNext.

	With requested properties, a line's property is its own ``utility_property``
	when requested, else the one property the request's rows of that item
	resolve to (see ``request_row_property``); a line that resolves to none or
	several is not guessed. Rent lines also get their property. The line takes
	the cost center of its request row, else of its property. Without a
	requested property, the line takes the cost center the request's rows of
	its item agree on, if any.

	Only a blank cost center, the company default or ERPNext's own default for
	the item is replaced, so a cost center chosen by hand is kept. Running it
	again changes nothing, so it runs both before validation (invoices inserted
	with ``ignore_validate``, such as the daily Item Price billing) and after the
	request is linked in ``validate``.
	"""
	if not is_item_price_approach():
		return

	if doc.get("is_return") or not doc.get("company"):
		return

	lines_by_request: dict[str, list] = {}
	for line in doc.get("items") or []:
		request = line_request(doc, line)
		if request:
			lines_by_request.setdefault(request, []).append(line)

	for request, lines in lines_by_request.items():
		fill_lines_of_request(doc, request, lines)


def fill_lines_of_request(doc: Document, request: str, lines: list) -> None:
	"""Fill the cost center, and property of rent lines, of the lines of one request."""
	request_doc = frappe.get_doc(USR_DOCTYPE, request)
	requested = requested_properties(request_doc)
	owners = service_item_owners(requested) if requested else {}
	request_rows: dict[str, list] = {}
	for row in request_doc.get("items") or []:
		if row.item_code and not row.get("meter_number"):
			request_rows.setdefault(row.item_code, []).append(row)

	company_default = frappe.get_cached_value("Company", doc.company, "cost_center")

	for line in lines:
		rows = request_rows.get(line.item_code)
		if not rows or line.get("meter_reading") or line.get("meter_number"):
			continue

		if requested:
			if line.get("utility_property") in requested:
				property_name = line.utility_property
			else:
				found = {request_row_property(row, requested, owners) for row in rows}
				property_name = found.pop() if len(found) == 1 else None
			if not property_name:
				continue

			if not line.get("utility_property") and property_name in (owners.get(line.item_code) or []):
				line.utility_property = property_name

		# A cost center chosen by hand that equals the item's or the company's
		# default cannot be told from ERPNext's own, so it may be replaced.
		if line.get("cost_center") not in (None, "", company_default, default_cost_center(line.item_code, doc.company)):
			continue

		if requested:
			chosen = {
				row.cost_center
				for row in rows
				if row.get("cost_center") and request_row_property(row, requested, owners) == property_name
			}
			cost_center = (chosen.pop() if len(chosen) == 1 else None) or resolve_primary_cost_center(
				property_name, line.item_code, doc.company
			)
		else:
			# No property to fall back on: only rows that all agree on a cost center give one.
			agreed = {row.get("cost_center") or None for row in rows}
			cost_center = agreed.pop() if len(agreed) == 1 else None

		if cost_center:
			line.cost_center = cost_center


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