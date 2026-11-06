"""What a released lease row still owns, under the Item Price approach.

A property row released on a Contract (Is Active unticked) records Released On,
the last day it held the property. The release day is inclusive: the row owns
its dates up to and including Released On, and nothing after. A released row
without a date owns nothing: one released before the field existed, or before
its lease started. A request row released before any Contract has no date and
owns nothing either.

A request row is never released by its Contract (see ``request_contract_lock``),
so readers of a request's leases look its release up on the Contract, matched
by request and property.
"""

from datetime import date

import frappe
from frappe import _
from frappe.utils import getdate, nowdate

from utility_billing.utility_billing.utils.request_prices import is_item_price_approach

ROW_DOCTYPE = "Contract Utility Property Item"
FIELD = "released_on"


def release_dates_stored() -> bool:
	"""Return whether Contract rows store Released On yet.

	The column comes with the migrate that syncs the field. Until then every
	released row reads as released without a date, so it owns nothing, as
	before the field.
	"""
	return frappe.db.has_column(ROW_DOCTYPE, FIELD)


def contract_releases(service_requests) -> dict[tuple[str, str], date | None]:
	"""Return the rows released on the live Contracts of some requests.

	Under Auto Repeat nothing is returned, so every reader stays as before.

	Returns:
		``{(request, property): released_on}``, ``None`` when no date was given.
	"""
	names = sorted({name for name in service_requests or () if name})
	if not names or not is_item_price_approach():
		return {}

	contract = frappe.qb.DocType("Contract")
	row = frappe.qb.DocType(ROW_DOCTYPE)
	stored = release_dates_stored()
	fields = [contract.utility_service_request, row.utility_property]
	if stored:
		fields.append(row[FIELD])

	rows = (
		frappe.qb.from_(row)
		.join(contract)
		.on(row.parent == contract.name)
		.select(*fields)
		.where(row.parenttype == "Contract")
		.where(contract.docstatus < 2)
		.where(contract.utility_service_request.isin(names))
		.where(row.is_active == 0)
	).run()

	return {
		(entry[0], entry[1]): (getdate(entry[2]) if stored and entry[2] else None) for entry in rows
	}


def owned_period(start, end, released: bool = False, released_on=None) -> tuple | None:
	"""Return the ``(start, end)`` a lease owns, or ``None`` when it owns nothing.

	A released lease ends on its Released On, or owns nothing without one or
	when it was released before it started.
	"""
	if not released:
		return start, end
	if not released_on:
		return None

	released_on = getdate(released_on)
	if start and released_on < getdate(start):
		return None

	return start, (min(getdate(end), released_on) if end else released_on)


def owns(start, end, day, released: bool = False, released_on=None) -> bool:
	"""Return whether a lease owns ``day``; blank bounds are open."""
	period = owned_period(start, end, released, released_on)
	if not period:
		return False

	day = getdate(day)
	start, end = period
	if start and day < getdate(start):
		return False

	return not (end and day > getdate(end))


def check_released_on(doc, saved=None) -> None:
	"""Check the Released On of a Contract's rows, and default it on a row released in this save.

	Released On belongs to a released row only, and lies within its lease.
	Under Item Price a row released in this save without a date gets today, as
	the form fills it, kept within the lease; released before its start it
	stays blank and owns nothing.

	Raises:
		frappe.ValidationError: When an active row has a date, or a date lies
			outside its lease.
	"""
	saved_rows = {row.name: row for row in (saved.get("properties") if saved else None) or []}

	for row in doc.get("properties") or []:
		start = row.start_date or doc.start_date
		end = row.end_date or doc.end_date

		if row.is_active:
			if row.get(FIELD):
				frappe.throw(
					_("Row #{0}: Released On is only for a released row. Untick Is Active first.").format(row.idx)
				)
			continue

		saved_row = saved_rows.get(row.name)
		if not row.get(FIELD) and saved_row and saved_row.is_active and is_item_price_approach():
			today = getdate(nowdate())
			if not (start and today < getdate(start)):
				row.set(FIELD, min(today, getdate(end)) if end else today)

		released_on = row.get(FIELD)
		if not released_on:
			continue

		released_on = getdate(released_on)
		if start and released_on < getdate(start):
			frappe.throw(
				_("Row #{0}: Released On {1} is before the lease of {2} starts on {3}.").format(
					row.idx, released_on, frappe.bold(row.utility_property), getdate(start)
				)
			)
		if end and released_on > getdate(end):
			frappe.throw(
				_("Row #{0}: Released On {1} is after the lease of {2} ends on {3}.").format(
					row.idx, released_on, frappe.bold(row.utility_property), getdate(end)
				)
			)


def check_not_on_request(doc) -> None:
	"""Refuse Released On on a request's rows; it is set on the Contract."""
	for row in doc.get("requested_properties") or []:
		if row.get(FIELD):
			frappe.throw(
				_("Row #{0}: Released On is set on the Contract, not on the Utility Service Request.").format(
					row.idx
				)
			)
