"""Read helpers and portal payloads for bookings.

Split from :mod:`utility_billing.api.portal.booking_core` to keep the write path
(creating a Utility Service Request) separate from the read path (listing,
serialising and building the booking timeline).
"""

from collections.abc import Iterable
from typing import Any

import frappe
from frappe import _
from frappe.utils import cint, flt, sanitize_html, strip_html

from utility_billing.api.portal.properties import PROPERTY_FIELDS
from utility_billing.api.portal.roles import get_portal_customers
from utility_billing.utility_billing.utils.lease_status import (
	derive_allocation_status,
	derive_lease_status,
	get_contract_rows,
	get_contracts_by_request,
)

REQUEST_DOCTYPE = "Utility Service Request"

REQUEST_ITEM_FIELDS = (
	"parent",
	"utility_property",
	"item_code",
	"start_date",
	"end_date",
	"is_active",
	"contract_length_months",
)


def get_properties_map(property_names: Iterable[str]) -> dict[str, dict]:
	"""Return descriptive fields of the given properties, keyed by name."""
	names = list(dict.fromkeys(name for name in property_names or () if name))
	if not names:
		return {}

	properties = frappe.db.get_all(
		"Utility Property",
		filters={"name": ("in", names)},
		fields=list(PROPERTY_FIELDS),
	)

	return {row.name: row for row in properties}


def get_request_rows(request_names: Iterable[str]) -> dict[str, list[dict]]:
	"""Return the requested property rows of the given requests."""
	names = list(dict.fromkeys(name for name in request_names or () if name))
	if not names:
		return {}

	rows = frappe.db.get_all(
		"Contract Utility Property Item",
		filters={"parent": ("in", names), "parenttype": REQUEST_DOCTYPE},
		fields=list(REQUEST_ITEM_FIELDS),
		order_by="idx asc",
	)

	grouped: dict[str, list[dict]] = {}
	for row in rows:
		grouped.setdefault(row.parent, []).append(row)

	return grouped


def get_request_documents(request_names: Iterable[str], customer_names: Iterable[str]) -> dict[str, dict]:
	"""Return the submitted invoices and orders linked to each request."""
	names = list(dict.fromkeys(name for name in request_names or () if name))
	customers = list(dict.fromkeys(name for name in customer_names or () if name))
	if not names or not customers:
		return {}

	invoices = frappe.db.get_all(
		"Sales Invoice",
		filters={
			"utility_service_request": ("in", names),
			"customer": ("in", customers),
			"docstatus": 1,
		},
		fields=[
			"name",
			"utility_service_request",
			"posting_date",
			"due_date",
			"grand_total",
			"outstanding_amount",
			"currency",
			"status",
		],
		order_by="posting_date desc",
	)

	orders = frappe.db.get_all(
		"Sales Order",
		filters={
			"utility_service_request": ("in", names),
			"customer": ("in", customers),
			"docstatus": 1,
		},
		fields=[
			"name",
			"utility_service_request",
			"transaction_date",
			"grand_total",
			"advance_paid",
			"per_billed",
			"currency",
			"status",
		],
		order_by="transaction_date desc",
	)

	documents: dict[str, dict] = {name: {"invoices": [], "orders": []} for name in names}
	for invoice in invoices:
		invoice["payable"] = flt(invoice.outstanding_amount) > 0
		documents[invoice.utility_service_request]["invoices"].append(invoice)

	for order in orders:
		payable = max(flt(order.grand_total) - flt(order.advance_paid), 0)
		order["payable_amount"] = payable
		order["payable"] = payable > 0 and flt(order.get("per_billed")) < 100 and order.status != "Closed"
		documents[order.utility_service_request]["orders"].append(order)

	return documents


def serialise_request(
	request: Any,
	*,
	contract: dict | None = None,
	contract_rows: list[dict] | None = None,
	properties: dict[str, dict] | None = None,
	documents: dict | None = None,
) -> dict:
	"""Build the portal representation of a booking request.

	Args:
		request: ``Utility Service Request`` document or dict.
		contract: Latest non-cancelled Contract of the request.
		contract_rows: Property rows of that Contract.
		properties: Descriptive property fields keyed by name.
		documents: Submitted invoices and orders linked to the request.

	Returns:
		Dict consumed by the bookings pages.
	"""
	data = request if isinstance(request, dict) else request.as_dict()
	properties = properties or {}
	documents = documents or {"invoices": [], "orders": []}
	has_contract = bool(contract)

	rows = []
	for row in data.get("requested_properties") or []:
		property_doc = properties.get(row.get("utility_property")) or {}
		rows.append(
			{
				"utility_property": row.get("utility_property"),
				"property_name": property_doc.get("property_name") or row.get("utility_property"),
				"item_code": row.get("item_code"),
				"start_date": row.get("start_date") or data.get("start_date"),
				"end_date": row.get("end_date") or data.get("end_date"),
				"is_active": cint(row.get("is_active")),
				"allocation_status": derive_allocation_status(
					row.get("is_active"),
					row.get("start_date") or data.get("start_date"),
					row.get("end_date") or data.get("end_date"),
				),
				"cover_image": property_doc.get("cover_image"),
				"unit_number": property_doc.get("unit_number"),
				"location": property_doc.get("location") or property_doc.get("territory"),
			}
		)

	return {
		"name": data.get("name"),
		"booking_reference": data.get("name"),
		"date": data.get("date"),
		"creation": data.get("creation"),
		"start_date": data.get("start_date"),
		"end_date": data.get("end_date"),
		"contract_length_months": data.get("contract_length_months"),
		"customer": data.get("customer"),
		"customer_name": data.get("customer_name"),
		"company": data.get("company"),
		"request_type": data.get("request_type"),
		"request_status": data.get("request_status"),
		"nrcpassport_no": data.get("nrcpassport_no"),
		"notes": strip_html(data.get("remarks") or "") or "",
		"docstatus": cint(data.get("docstatus")),
		"lease_status": derive_lease_status(data.get("docstatus"), contract, contract_rows),
		"contract": contract.get("name") if contract else None,
		"contract_status": contract.get("status") if contract else None,
		"is_signed": cint(contract.get("is_signed")) if contract else 0,
		"properties": rows,
		"documents": documents,
		"can_modify": cint(data.get("docstatus")) in (0, 1) and not has_contract,
		"can_cancel": cint(data.get("docstatus")) in (0, 1) and not has_contract,
		"can_extend": cint(data.get("docstatus")) == 1,
		"can_pay": any(
			doc.get("payable", flt(doc.get("outstanding_amount")) > 0)
			for doc in [*documents.get("invoices", []), *documents.get("orders", [])]
		),
	}


def build_timeline(request: Any, contract: dict | None = None, documents: dict | None = None) -> list[dict]:
	"""Return the booking events, newest first.

	Args:
		request: ``Utility Service Request`` document or dict.
		contract: Latest non-cancelled Contract of the request.
		documents: Submitted invoices and orders linked to the request.

	Returns:
		List of ``{label, date, type}`` events.
	"""
	data = request if isinstance(request, dict) else request.as_dict()
	documents = documents or {"invoices": [], "orders": []}
	events = []

	if data.get("creation"):
		events.append({"label": _("Booking created"), "date": data["creation"], "type": "created"})

	if cint(data.get("docstatus")) == 1:
		events.append(
			{
				"label": _("Booking confirmed"),
				"date": data.get("modified") or data.get("creation"),
				"type": "confirmed",
			}
		)
	elif cint(data.get("docstatus")) == 2:
		events.append(
			{
				"label": _("Booking cancelled"),
				"date": data.get("modified") or data.get("creation"),
				"type": "cancelled",
			}
		)

	if contract:
		events.append(
			{
				"label": _("Contract {0} created").format(contract.get("name")),
				"date": contract.get("creation"),
				"type": "contract",
			}
		)

	for invoice in documents.get("invoices", []):
		events.append(
			{
				"label": _("Invoice {0} raised").format(invoice.get("name")),
				"date": invoice.get("posting_date"),
				"type": "invoice",
			}
		)

	for order in documents.get("orders", []):
		events.append(
			{
				"label": _("Order {0} raised").format(order.get("name")),
				"date": order.get("transaction_date"),
				"type": "order",
			}
		)

	comments = frappe.db.get_all(
		"Comment",
		filters={
			"reference_doctype": REQUEST_DOCTYPE,
			"reference_name": data.get("name"),
			"comment_type": ("in", ["Comment", "Info"]),
		},
		fields=["content", "creation", "comment_by"],
		order_by="creation desc",
		limit=50,
	)
	for comment in comments:
		events.append(
			{
				"label": strip_html(comment.content) or _("Comment"),
				"date": comment.creation,
				"type": "comment",
				"by": comment.comment_by,
			}
		)

	return sorted(
		(event for event in events if event.get("date")),
		key=lambda event: str(event["date"]),
		reverse=True,
	)


def add_booking_comment(request_name: str, content: str) -> None:
	"""Append an activity comment to a booking request."""
	frappe.get_doc(
		{
			"doctype": "Comment",
			"comment_type": "Info",
			"reference_doctype": REQUEST_DOCTYPE,
			"reference_name": request_name,
			"content": sanitize_html(content),
		}
	).insert(ignore_permissions=True)


def serialise_many(requests: list, customer_names: list[str], rows_by_request: dict) -> list[dict]:
	"""Serialise several booking requests with batched lookups."""
	contracts = get_contracts_by_request(request.name for request in requests)
	rows_by_contract = get_contract_rows(contract.get("name") for contract in contracts.values())
	property_names = [
		row.utility_property for rows in rows_by_request.values() for row in rows if row.utility_property
	]
	properties = get_properties_map(property_names)
	documents = get_request_documents([request.name for request in requests], customer_names)

	bookings = []
	for request in requests:
		contract = contracts.get(request.name)
		request["requested_properties"] = rows_by_request.get(request.name, [])
		bookings.append(
			serialise_request(
				request,
				contract=contract,
				contract_rows=rows_by_contract.get(contract.get("name")) if contract else None,
				properties=properties,
				documents=documents.get(request.name, {"invoices": [], "orders": []}),
			)
		)

	return bookings


def serialise_doc(request) -> tuple[dict, list[dict]]:
	"""Serialise a request document and build its timeline."""
	customer = request.customer or request.party_name
	contract = get_contracts_by_request([request.name]).get(request.name)
	rows_by_contract = get_contract_rows([contract.get("name")] if contract else [])
	property_names = [row.utility_property for row in request.requested_properties]
	properties = get_properties_map(property_names)
	documents = get_request_documents([request.name], [customer] if customer else []).get(
		request.name, {"invoices": [], "orders": []}
	)

	booking = serialise_request(
		request,
		contract=contract,
		contract_rows=rows_by_contract.get(contract.get("name")) if contract else None,
		properties=properties,
		documents=documents,
	)
	timeline = build_timeline(request, contract, documents)
	return booking, timeline


def serialise_one(name: str) -> tuple[dict, list[dict]]:
	"""Load and serialise a single request."""
	return serialise_doc(frappe.get_doc(REQUEST_DOCTYPE, name))


def get_own_request(name: str):
	"""Return a request after checking it belongs to the caller."""
	customers = {customer["name"] for customer in get_portal_customers()}
	if not customers:
		raise frappe.PermissionError

	request = frappe.get_doc(REQUEST_DOCTYPE, name)
	if request.customer not in customers and request.party_name not in customers:
		raise frappe.PermissionError

	return request


def ensure_modifiable(request) -> None:
	"""Raise unless the booking can still be changed or cancelled."""
	if cint(request.docstatus) not in (0, 1):
		frappe.throw(_("This booking can no longer be changed."))

	if request.name in get_contracts_by_request([request.name]):
		frappe.throw(
			_(
				"This booking already has a Contract. Ask the property manager to "
				"change or cancel the tenancy instead."
			)
		)
