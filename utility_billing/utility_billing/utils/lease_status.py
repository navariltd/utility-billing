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

Under Item Price a row released on the Contract stays live up to and including
its Released On (see ``release``), so a Contract set Inactive because every row
was released stays ``Active`` until the last of those dates.
* ``Cancelled``           – the request was cancelled.
"""

from collections.abc import Iterable

import frappe
from frappe.utils import cint, getdate, today

from utility_billing.utility_billing.utils.release import FIELD as RELEASED_ON
from utility_billing.utility_billing.utils.release import (
	contract_row_release,
	holds_on,
	owned_period,
	release_dates_stored,
)

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

	fields = list(ROW_FIELDS) + ([RELEASED_ON] if release_dates_stored() else [])
	rows = frappe.db.get_all(
		ROW_DOCTYPE,
		filters={"parent": ("in", names), "parenttype": CONTRACT_DOCTYPE},
		fields=fields,
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

	rows = contract_rows or []
	day = reference_date or today()
	holding = [row for row in rows if row_holds_on(row, day)]

	# Inactive because every row was released: live until the last Released On
	all_released = bool(rows) and not any(cint(row.get("is_active")) for row in rows)
	if (contract.get("status") or "") == "Inactive" and not (all_released and holding):
		return EXPIRED

	if rows and not holding:
		return EXPIRED

	return ACTIVE


def row_holds_on(row, day) -> bool:
	"""Return whether a Contract row still holds its property on ``day``, Released On included."""
	released, released_on = contract_row_release(row)
	return holds_on(row.get("start_date"), row.get("end_date"), day, released, released_on)


def derive_allocation_status(
	is_active: int | bool,
	start_date: str | None,
	end_date: str | None,
	reference_date: str | None = None,
	released: bool = False,
	released_on=None,
) -> str:
	"""Describe a single Contract property allocation.

	A row released on its Contract (``released``, or ``is_active`` unticked)
	stays ``Active`` or ``Upcoming`` up to and including its Released On, then
	is ``Released``; without a date it is ``Released`` at once.

	Returns:
		``Released``, ``Expired``, ``Upcoming`` or ``Active``.
	"""
	current_date = getdate(reference_date or today())
	if released or not cint(is_active):
		period = owned_period(start_date, end_date, True, released_on)
		if not period or getdate(period[1]) < current_date:
			return "Released"
		end_date = period[1]

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
