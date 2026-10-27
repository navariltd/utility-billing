"""Live availability of Utility Properties.

``Utility Property.status`` is the source of truth for maintenance and manual
blocks, but it is only updated when a Contract changes state. A submitted
Utility Service Request already reserves its property, so it must be taken into
account as well; otherwise a unit could be booked twice between the request
and the Contract.

A property is *held* while any submitted request has an active row for it whose
effective end date is today or later, or which has no end date at all. Future
leases hold the property immediately: the unit has been promised to somebody,
even if the lease has not started yet.
"""

from collections.abc import Iterable

import frappe
from frappe.query_builder import DocType
from frappe.utils import getdate, today

REQUEST_DOCTYPE = "Utility Service Request"
ROW_DOCTYPE = "Contract Utility Property Item"


def get_live_leases(
	reference_date: str | None = None,
	property_names: Iterable[str] | None = None,
) -> list[dict]:
	"""Return the active lease rows of submitted requests.

	Args:
		reference_date: Date used to decide whether a lease has ended.
			Defaults to today.
		property_names: Optional properties to restrict the result to.

	Returns:
		One dict per active row with ``utility_property``, ``start``, ``end``
		and ``is_current``. ``end`` is ``None`` for an open ended lease.
	"""
	names = list(dict.fromkeys(name for name in property_names or () if name))
	if property_names is not None and not names:
		return []

	row = DocType(ROW_DOCTYPE)
	request = DocType(REQUEST_DOCTYPE)

	query = (
		frappe.qb.from_(row)
		.join(request)
		.on(row.parent == request.name)
		.select(
			row.utility_property,
			row.start_date,
			row.end_date,
			request.start_date.as_("request_start"),
			request.end_date.as_("request_end"),
		)
		.where(row.parenttype == REQUEST_DOCTYPE)
		.where(row.is_active == 1)
		.where(request.docstatus == 1)
	)

	if names:
		query = query.where(row.utility_property.isin(names))

	rows = query.run(as_dict=True)
	current_date = getdate(reference_date or today())

	leases = []
	for entry in rows:
		start = entry.start_date or entry.request_start
		end = entry.end_date or entry.request_end
		leases.append(
			{
				"utility_property": entry.utility_property,
				"start": start,
				"end": end,
				"is_current": not end or getdate(end) >= current_date,
			}
		)

	return leases


def get_held_properties(
	reference_date: str | None = None,
	property_names: Iterable[str] | None = None,
) -> set[str]:
	"""Return the properties currently promised to a submitted lease.

	Args:
		reference_date: Date used to decide whether a lease has ended.
		property_names: Optional properties to restrict the result to.

	Returns:
		Names of the properties that cannot be booked again.
	"""
	return {
		lease["utility_property"]
		for lease in get_live_leases(reference_date, property_names)
		if lease["is_current"]
	}


def is_property_available(
	property_doc_or_name,
	*,
	status: str | None = None,
	is_group: int | None = None,
	reference_date: str | None = None,
) -> bool:
	"""Return whether a property can be booked on ``reference_date``.

	Args:
		property_doc_or_name: ``Utility Property`` document, dict or name.
		status: Availability status when already known.
		is_group: Group flag when already known.
		reference_date: Date used to decide whether a lease has ended.

	Returns:
		``True`` when the property is a non-group, ``Available`` unit without
		a live submitted lease.
	"""
	if isinstance(property_doc_or_name, str):
		property_name = property_doc_or_name
	else:
		property_name = property_doc_or_name.get("name")

	if not property_name:
		return False

	if status is None or is_group is None:
		fields = frappe.db.get_value(
			"Utility Property",
			property_name,
			["status", "is_group"],
			as_dict=True,
		)
		if not fields:
			return False
		status = fields.status
		is_group = fields.is_group

	if status != "Available" or is_group:
		return False

	return property_name not in get_held_properties(reference_date, [property_name])
