"""Whitelisted helpers of the Sales Invoice item grid.

The Sales Invoice form calls these to keep an invoice line in step with its
Deferred Posting Date and with the utility property its item belongs to.
"""

import frappe
from frappe.utils import flt

from utility_billing.utility_billing.utils.item_price_scope import is_item_price_approach
from utility_billing.utility_billing.utils.item_rate import get_rate_for_date
from utility_billing.utility_billing.utils.line_request import (
	REQUEST_FIELD,
	get_governed_rows,
	move_header_to_lines,
	resolve_lines,
	uses_header_path,
)
from utility_billing.utility_billing.utils.service_item import (
	get_property_of_service_item,
	get_service_item_of_property,
)
from utility_billing.utility_billing.utils.utility_item_classifier import (
	get_primary_items,
	get_request_lines,
	match_error_message,
	match_requests,
)


@frappe.whitelist()
def get_line_rate(
	item_code: str,
	posting_date: str,
	customer: str | None = None,
	price_list: str | None = None,
	uom: str | None = None,
	qty: float | None = None,
	conversion_factor: float | None = None,
	plc_conversion_rate: float | None = None,
	conversion_rate: float | None = None,
	utility_service_request: str | None = None,
) -> float | None:
	"""Return the rate of an item valid on a date.

	Used when the revenue of an invoice line is deferred: the line has to be
	billed at the rate that is valid on its Deferred Posting Date.

	Args:
		item_code: Item of the invoice line.
		posting_date: Date the rate has to be valid on.
		customer: Customer of the invoice, if any.
		price_list: Price list of the invoice, if any.
		uom: UOM of the invoice line, if any.
		qty: Quantity of the invoice line, if any.
		conversion_factor: Stock UOM to UOM conversion factor of the line.
		plc_conversion_rate: Price list currency to company currency rate.
		conversion_rate: Transaction currency to company currency rate.
		utility_service_request: Request linked to the invoice. Under the Item
			Price approach its primary items are priced from its own prices only.

	Returns:
		The rate in the currency of the transaction, rounded to the line's
		precision, or None when no Item Price covers the item, the customer and
		the date.
	"""
	service_request = (
		utility_service_request
		if utility_service_request
		and is_item_price_approach()
		and item_code in get_primary_items(utility_service_request)
		else None
	)

	rate = get_rate_for_date(
		item_code,
		posting_date,
		customer=customer,
		price_list=price_list,
		uom=uom,
		qty=qty,
		conversion_factor=conversion_factor or 1,
		plc_conversion_rate=plc_conversion_rate or 1,
		conversion_rate=conversion_rate or 1,
		service_request=service_request,
	)
	if rate is None:
		return None

	# Rounded as the line stores it: a currency conversion leaves float noise
	# (205500.00000000003), which the form would take for another price and set
	# on a saved draft, leaving it unsaved.
	return flt(rate, frappe.get_precision("Sales Invoice Item", "price_list_rate"))


@frappe.whitelist()
def get_line_utility_property(item_code: str) -> str | None:
	"""Return the utility property billed through an item.

	Args:
		item_code: Item of the invoice line.

	Returns:
		The ``Utility Property`` name, or None when the item is not the service
		item of a property or the property is not readable by the user.
	"""
	if not frappe.has_permission("Utility Property", "read"):
		return None

	return get_property_of_service_item(item_code)


@frappe.whitelist()
def get_line_item(utility_property: str) -> str | None:
	"""Return the service item to bill for a utility property.

	Args:
		utility_property: ``Utility Property`` name.

	Returns:
		The service item code, or None when the property has no service item and
		auto creation is disabled, or the property is not readable by the user.
	"""
	if not frappe.has_permission("Utility Property", "read"):
		return None

	return get_service_item_of_property(utility_property)


@frappe.whitelist()
def match_utility_service_requests(
	customer: str,
	item_codes: list | str,
	new_item_code: str | None = None,
	billing_dates: dict | str | None = None,
) -> dict:
	"""Return the Utility Service Requests able to govern an invoice's utility lines.

	Args:
		customer: Customer of the invoice.
		item_codes: Item codes on the invoice; non utility items are ignored.
		new_item_code: Item just added, named in a blocking message.
		billing_dates: Optional mapping of item code to its billing dates, used to
			pick the one request whose lease covers them when several match.

	Returns:
		``applies`` (False when the invoice has no utility item or rates are not
		billed by Item Price) and, when it applies, ``status``, ``candidates``,
		``missing`` and the blocking ``message`` if any.
	"""
	if not is_item_price_approach():
		return {"applies": False}

	frappe.has_permission("Utility Service Request", "read", throw=True)

	codes = frappe.parse_json(item_codes) if isinstance(item_codes, str) else item_codes
	dates = frappe.parse_json(billing_dates) if isinstance(billing_dates, str) else billing_dates
	match = match_requests(customer, codes, dates)
	if not match.status:
		return {"applies": False}

	return {
		"applies": True,
		"status": match.status,
		"candidates": match.candidates,
		"missing": match.missing,
		"message": match_error_message(match, customer, new_item_code),
	}


@frappe.whitelist()
def get_utility_service_request_lines(utility_service_request: str) -> list[dict]:
	"""Return the governed utility lines of a Utility Service Request.

	Args:
		utility_service_request: ``Utility Service Request`` name.

	Returns:
		One entry per utility item with its ``role``, ``rate``, ``qty`` and ``uom``.
	"""
	if not is_item_price_approach():
		return []

	frappe.has_permission(
		"Utility Service Request", "read", doc=utility_service_request, throw=True
	)

	return list(get_request_lines(utility_service_request).values())


@frappe.whitelist()
def resolve_invoice_lines(doc: dict | str) -> dict:
	"""Return the Utility Service Request of each utility line of an invoice in the form.

	Resolves the lines the way saving the invoice does (see ``line_request``),
	without saving or raising, so the form can fill each line's request, let
	the user pick one where several qualify, and show why a line has none.

	Args:
		doc: The Sales Invoice as it is in the form.

	Returns:
		``applies`` (False when rates are not billed by Item Price or the
		invoice is not a draft), ``header_path`` (True for a draft Auto Repeat
		generated from an invoice linked through its header) and ``rows``: per
		line name, its ``status``, ``service_request``, ``utility_property``,
		``candidates``, ``editable``, ``message`` and, once resolved, the
		``role`` and request ``rate`` of its item.
	"""
	if not is_item_price_approach():
		return {"applies": False}

	frappe.has_permission("Utility Service Request", "read", throw=True)

	doc = frappe.get_doc(frappe.parse_json(doc) if isinstance(doc, str) else doc)
	if doc.doctype != "Sales Invoice" or doc.docstatus != 0 or doc.get("is_return") or not doc.customer:
		return {"applies": False}

	rows = get_governed_rows(doc)
	if uses_header_path(doc):
		lines = get_request_lines(doc.get(REQUEST_FIELD))
		return {
			"applies": True,
			"header_path": True,
			"rows": {
				row.name: {"status": "resolved", "service_request": doc.get(REQUEST_FIELD), **lines[row.item_code]}
				for row in rows
				if row.item_code in lines
			},
		}

	move_header_to_lines(doc, rows)
	results = resolve_lines(doc, rows)
	request_lines = {}
	out = {}
	for row in rows:
		entry = results[row.name or str(row.idx)]
		if entry.service_request:
			if entry.service_request not in request_lines:
				request_lines[entry.service_request] = get_request_lines(entry.service_request)
			line = request_lines[entry.service_request].get(row.item_code)
			if line:
				entry.update(role=line.role, rate=line.rate)
		out[row.name] = entry

	return {"applies": True, "header_path": False, "rows": out}


@frappe.whitelist()
def get_request_invoices(utility_service_request: str) -> list[dict]:
	"""Return the Sales Invoices of a Utility Service Request, found through their header or their lines.

	Connections only follow the header while the header field exists, so
	invoices linked through their lines are listed here.

	Args:
		utility_service_request: ``Utility Service Request`` name.

	Returns:
		The invoices the user can read, newest first, at most 100.
	"""
	frappe.has_permission("Utility Service Request", "read", doc=utility_service_request, throw=True)
	if not frappe.has_permission("Sales Invoice", "read"):
		return []

	names = frappe.db.sql_list(
		"""
		select distinct invoice.name
		from `tabSales Invoice` invoice
		join `tabSales Invoice Item` line
			on line.parent = invoice.name and line.parenttype = 'Sales Invoice'
		where coalesce(nullif(line.utility_service_request, ''), invoice.utility_service_request) = %(request)s
		""",
		{"request": utility_service_request},
	)
	if not names:
		return []

	return frappe.get_list(
		"Sales Invoice",
		filters={"name": ("in", names)},
		fields=["name", "status", "docstatus", "posting_date", "grand_total", "outstanding_amount", "currency"],
		order_by="posting_date desc, name desc",
		limit_page_length=100,
	)


@frappe.whitelist()
def get_property_of_cost_center(cost_center: str) -> str | None:
	"""Return the one Utility Property using a cost center, or None when none or several do.

	Args:
		cost_center: ``Cost Center`` name.
	"""
	if not frappe.has_permission("Utility Property", "read"):
		return None

	properties = frappe.get_all("Utility Property", filters={"cost_center": cost_center}, pluck="name", limit=2)
	return properties[0] if len(properties) == 1 else None
