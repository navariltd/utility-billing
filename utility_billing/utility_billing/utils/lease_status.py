"""Lease status of a Utility Service Request and its property allocations.

A request becomes a lease through the Contract made from it. The portal shows a
single readable status, so this module derives it from the request's docstatus,
the linked Contract (draft, unsigned, active, inactive) and the Contract's
property rows (``is_active`` and dates).

Statuses returned by :func:`derive_lease_status`:

* ``Draft``               – the request has not been submitted.
* ``Reserved``            – submitted, no Contract yet.
* ``Contract Draft``      – the Contract exists but is not submitted.
* ``Awaiting Signature``  – the Contract is submitted but not signed.
* ``Active``              – signed Contract with a live property allocation.
* ``Expired``             – Contract inactive, or every allocation ended/released.
* ``Cancelled``           – the request was cancelled.
"""

from collections.abc import Iterable

import frappe
from frappe.utils import cint, getdate, today

REQUEST_DOCTYPE = "Utility Service Request"
CONTRACT_DOCTYPE = "Contract"
ROW_DOCTYPE = "Contract Utility Property Item"

DRAFT = "Draft"
RESERVED = "Reserved"
CONTRACT_DRAFT = "Contract Draft"
AWAITING_SIGNATURE = "Awaiting Signature"
ACTIVE = "Active"
EXPIRED = "Expired"
CANCELLED = "Cancelled"

CURRENT_STATUSES = (RESERVED, CONTRACT_DRAFT, AWAITING_SIGNATURE, ACTIVE)

CONTRACT_FIELDS = (
	"name",
	"utility_service_request",
	"status",
	"is_signed",
	"docstatus",
	"start_date",
	"end_date",
	"creation",
)

ROW_FIELDS = (
	"parent",
	"utility_property",
	"start_date",
	"end_date",
	"is_active",
)


def get_contracts_by_request(request_names: Iterable[str]) -> dict[str, dict]:
	"""Return the latest Contract of each request.

	Args:
		request_names: ``Utility Service Request`` names.

	Returns:
		Mapping of request name to the newest non-cancelled Contract.
	"""
	names = list(dict.fromkeys(name for name in request_names or () if name))
	if not names:
		return {}

	contracts = frappe.db.get_all(
		CONTRACT_DOCTYPE,
		filters={
			"utility_service_request": ("in", names),
			"docstatus": ("!=", 2),
		},
		fields=list(CONTRACT_FIELDS),
		order_by="creation desc",
	)

	by_request: dict[str, dict] = {}
	for contract in contracts:
		by_request.setdefault(contract.utility_service_request, contract)

	return by_request


def get_contract_rows(contract_names: Iterable[str]) -> dict[str, list[dict]]:
	"""Return the property rows of each Contract, grouped by Contract name."""
	names = list(dict.fromkeys(name for name in contract_names or () if name))
	if not names:
		return {}

	rows = frappe.db.get_all(
		ROW_DOCTYPE,
		filters={"parent": ("in", names), "parenttype": CONTRACT_DOCTYPE},
		fields=list(ROW_FIELDS),
		order_by="idx asc",
	)

	grouped: dict[str, list[dict]] = {}
	for row in rows:
		grouped.setdefault(row.parent, []).append(row)

	return grouped


def derive_lease_status(
	docstatus: int,
	contract: dict | None = None,
	contract_rows: list[dict] | None = None,
	reference_date: str | None = None,
) -> str:
	"""Derive the portal lease status of a request.

	Args:
		docstatus: ``Utility Service Request.docstatus``.
		contract: Latest non-cancelled Contract of the request, if any.
		contract_rows: Property rows of that Contract.
		reference_date: Date used to detect expired allocations.

	Returns:
		One of ``Draft``, ``Reserved``, ``Contract Draft``,
		``Awaiting Signature``, ``Active``, ``Expired`` or ``Cancelled``.
	"""
	if docstatus == 0:
		return DRAFT
	if docstatus == 2:
		return CANCELLED

	if not contract:
		return RESERVED

	if cint(contract.get("docstatus")) == 0:
		return CONTRACT_DRAFT

	if not cint(contract.get("is_signed")):
		return AWAITING_SIGNATURE

	if (contract.get("status") or "") == "Inactive":
		return EXPIRED

	rows = contract_rows or []
	if rows and not any(
		cint(row.get("is_active"))
		and (not row.get("end_date") or getdate(row["end_date"]) >= getdate(reference_date or today()))
		for row in rows
	):
		return EXPIRED

	return ACTIVE


def derive_allocation_status(
	is_active: int | bool,
	start_date: str | None,
	end_date: str | None,
	reference_date: str | None = None,
) -> str:
	"""Describe a single Contract property allocation.

	Returns:
		``Released``, ``Expired``, ``Upcoming`` or ``Active``.
	"""
	if not cint(is_active):
		return "Released"

	current_date = getdate(reference_date or today())
	if end_date and getdate(end_date) < current_date:
		return "Expired"
	if start_date and getdate(start_date) > current_date:
		return "Upcoming"

	return "Active"


def decorate_service_requests(requests: list[dict]) -> list[dict]:
	"""Attach the derived lease status to the given request rows.

	Args:
		requests: Rows holding at least ``name`` and ``docstatus``.

	Returns:
		The same rows, each with ``lease_status``, ``contract``,
		``contract_status`` and ``is_signed``.
	"""
	if not requests:
		return requests

	contracts = get_contracts_by_request(row["name"] for row in requests)
	contract_rows = get_contract_rows(contract.get("name") for contract in contracts.values())

	for row in requests:
		contract = contracts.get(row["name"])
		row["lease_status"] = derive_lease_status(
			row.get("docstatus"),
			contract,
			contract_rows.get(contract.get("name")) if contract else None,
		)
		row["contract"] = contract.get("name") if contract else None
		row["contract_status"] = contract.get("status") if contract else None
		row["is_signed"] = cint(contract.get("is_signed")) if contract else 0

	return requests
