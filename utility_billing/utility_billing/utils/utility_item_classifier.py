"""Classification of the utility lines of a Sales Invoice.

Under the Item Price billing approach a Utility Service Request (USR) is the
source of truth for the utility items a customer may be billed for. Only items
flagged ``is_utility_item`` are governed; every other item is left alone.

A governed item on a request is either:

* **primary** - the rent service item of one of the request's properties
  (``Utility Property.service_item``), billed at the Item Price valid on the
  billing date;
* **secondary** - any other utility item row of the request, billed at the
  rate recorded on that request row.
"""

import frappe
from frappe import _
from frappe.utils import flt

USR_DOCTYPE = "Utility Service Request"
USR_ITEM_DOCTYPE = "Utility Service Request Item"
USR_PROPERTY_DOCTYPE = "Contract Utility Property Item"

PRIMARY = "primary"
SECONDARY = "secondary"

MATCH_SINGLE = "single"
MATCH_MULTIPLE = "multiple"
MATCH_MISSING = "missing"
MATCH_CONFLICT = "conflict"


def get_utility_items(item_codes) -> set[str]:
	"""Return the codes among ``item_codes`` whose Item is a utility item.

	Args:
		item_codes: Item codes to check. Empty values are ignored.

	Returns:
		The item codes flagged ``is_utility_item``.
	"""
	codes = list({code for code in item_codes or [] if code})
	if not codes:
		return set()

	return set(
		frappe.get_all("Item", filters={"name": ("in", codes), "is_utility_item": 1}, pluck="name")
	)


def get_primary_items(service_request: str) -> set[str]:
	"""Return the rent service items of a request's properties.

	The service item is read from each property rather than from the request
	row, so a property whose item changed is still classified correctly.

	Args:
		service_request: ``Utility Service Request`` name.

	Returns:
		Service item codes of the request's requested properties.
	"""
	properties = frappe.get_all(
		USR_PROPERTY_DOCTYPE,
		filters={
			"parent": service_request,
			"parenttype": USR_DOCTYPE,
			"utility_property": ("is", "set"),
		},
		pluck="utility_property",
	)
	if not properties:
		return set()

	return set(
		frappe.get_all(
			"Utility Property",
			filters={"name": ("in", properties), "service_item": ("is", "set")},
			pluck="service_item",
		)
	)


def get_request_lines(service_request: str) -> dict[str, frappe._dict]:
	"""Return the governed utility lines of a request, keyed by item code.

	When an item is listed more than once the first row wins.

	Args:
		service_request: ``Utility Service Request`` name.

	Returns:
		Mapping of item code to ``item_code``, ``role`` (primary or secondary),
		``rate``, ``qty`` and ``uom`` of the request row.
	"""
	rows = frappe.get_all(
		USR_ITEM_DOCTYPE,
		filters={"parent": service_request, "parenttype": USR_DOCTYPE},
		fields=["item_code", "rate", "qty", "uom"],
		order_by="idx asc",
	)
	utility_items = get_utility_items(row.item_code for row in rows)
	primary_items = get_primary_items(service_request)

	lines = {}
	for row in rows:
		if row.item_code not in utility_items or row.item_code in lines:
			continue

		lines[row.item_code] = frappe._dict(
			item_code=row.item_code,
			role=PRIMARY if row.item_code in primary_items else SECONDARY,
			rate=flt(row.rate),
			qty=flt(row.qty) or 1,
			uom=row.uom,
		)

	return lines


def get_requests_by_item(customer: str, item_codes) -> dict[str, set[str]]:
	"""Return, per item, the submitted requests of a customer listing it.

	Args:
		customer: Customer the requests belong to.
		item_codes: Item codes to look up.

	Returns:
		Mapping of item code to the names of the requests listing it.
	"""
	request = frappe.qb.DocType(USR_DOCTYPE)
	row = frappe.qb.DocType(USR_ITEM_DOCTYPE)

	rows = (
		frappe.qb.from_(row)
		.join(request)
		.on(row.parent == request.name)
		.select(row.item_code, request.name.as_("service_request"))
		.where(row.parenttype == USR_DOCTYPE)
		.where(request.docstatus == 1)
		.where(request.customer == customer)
		.where(row.item_code.isin(list(item_codes)))
	).run(as_dict=True)

	requests_by_item = {code: set() for code in item_codes}
	for entry in rows:
		requests_by_item[entry.item_code].add(entry.service_request)

	return requests_by_item


def match_requests(customer: str, item_codes) -> frappe._dict:
	"""Find the requests of a customer covering every utility item given.

	Args:
		customer: Customer of the invoice.
		item_codes: Item codes on the invoice; non utility items are ignored.

	Returns:
		``status`` (``None`` when no utility item is given, otherwise one of the
		``MATCH_*`` values), ``items`` (utility items considered), ``candidates``
		(requests covering all of them), ``missing`` (items on no request) and
		``requests_by_item``.
	"""
	utility_items = sorted(get_utility_items(item_codes))
	match = frappe._dict(
		status=None, items=utility_items, candidates=[], missing=[], requests_by_item={}
	)
	if not customer or not utility_items:
		return match

	requests_by_item = get_requests_by_item(customer, utility_items)
	match.requests_by_item = {code: sorted(names) for code, names in requests_by_item.items()}
	match.missing = [code for code in utility_items if not requests_by_item[code]]

	if match.missing:
		match.status = MATCH_MISSING
		return match

	match.candidates = sorted(set.intersection(*requests_by_item.values()))

	if not match.candidates:
		match.status = MATCH_CONFLICT
	elif len(match.candidates) == 1:
		match.status = MATCH_SINGLE
	else:
		match.status = MATCH_MULTIPLE

	return match


def match_error_message(match: frappe._dict, customer: str, item_code: str | None = None) -> str | None:
	"""Return the message blocking an invoice whose utility items cannot be matched.

	Args:
		match: Result of ``match_requests``.
		customer: Customer of the invoice.
		item_code: Item just added, named in the message when given.

	Returns:
		The message, or ``None`` when the match does not block the invoice.
	"""
	if match.status == MATCH_MISSING:
		return _(
			"{0} is not on any submitted Utility Service Request of {1}. Add it to one of the "
			"customer's Utility Service Requests, or create one, before billing it."
		).format(", ".join(frappe.bold(code) for code in match.missing), frappe.bold(customer))

	if match.status == MATCH_CONFLICT:
		coverage = "<br>".join(
			f"{frappe.bold(code)}: {', '.join(names)}" for code, names in match.requests_by_item.items()
		)
		if item_code:
			return _(
				"{0} cannot be billed with the other utility items on this invoice: no single "
				"Utility Service Request of {1} covers them all. Bill it on a separate invoice, or "
				"add all of them to the same Utility Service Request.<br><br>{2}"
			).format(frappe.bold(item_code), frappe.bold(customer), coverage)

		return _(
			"The utility items on this invoice are not all on the same Utility Service Request "
			"of {0}. Bill them on separate invoices, or add them all to the same Utility Service "
			"Request.<br><br>{1}"
		).format(frappe.bold(customer), coverage)

	return None
