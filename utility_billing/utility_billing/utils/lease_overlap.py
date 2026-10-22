"""Overlapping lease detection for Utility Service Requests.

A property can be leased only once on any given day. Every requested property
row is checked on its own lease - its row dates, falling back to the request's
Contract Details - against the active rows of every other submitted request
for the same property, whatever the customer. Two customers holding the same
property for the same days is a double booking; one customer holding it twice
leaves Item Prices (keyed by item and customer) unable to tell the leases apart.
"""

import frappe
from frappe import _
from frappe.utils import getdate

USR_DOCTYPE = "Utility Service Request"
ROW_DOCTYPE = "Contract Utility Property Item"


def validate_no_overlapping_leases(doc) -> None:
	"""Block a request leasing a property already leased for overlapping dates.

	Inactive rows have released their property and are ignored. A blank end
	is open ended, so it overlaps every later lease.

	Args:
		doc: ``Utility Service Request`` being submitted or updated.

	Raises:
		frappe.ValidationError: Naming the property, the row, both leases and
			the request already holding the property.
	"""
	leases = [
		frappe._dict(
			utility_property=row.utility_property,
			idx=row.idx,
			start=row.start_date or doc.start_date,
			end=row.end_date or doc.end_date,
		)
		for row in doc.get("requested_properties") or []
		if row.utility_property and row.get("is_active") != 0
	]

	for index, lease in enumerate(leases):
		for other in leases[index + 1 :]:
			if lease.utility_property == other.utility_property and periods_overlap(
				lease.start, lease.end, other.start, other.end
			):
				frappe.throw(
					_(
						"Property {0} is requested twice for overlapping dates, in rows {1} "
						"and {2}. A property cannot be leased twice for the same dates."
					).format(frappe.bold(lease.utility_property), lease.idx, other.idx)
				)

	for lease in leases:
		for other in get_submitted_leases(lease.utility_property, exclude=doc.name):
			if periods_overlap(lease.start, lease.end, other.start, other.end):
				frappe.throw(
					_(
						"Property {0} in row {1} is already leased to {2} {3} on Utility Service "
						"Request {4}, which overlaps this lease {5}. A property cannot be leased "
						"twice for the same dates."
					).format(
						frappe.bold(lease.utility_property),
						lease.idx,
						frappe.bold(other.customer),
						describe_period(other.start, other.end),
						frappe.bold(other.service_request),
						describe_period(lease.start, lease.end),
					)
				)


def get_submitted_leases(utility_property: str, exclude: str | None = None) -> list[frappe._dict]:
	"""Return the active leases of a property on submitted requests.

	Args:
		utility_property: ``Utility Property`` name.
		exclude: Request to leave out, normally the one being checked.

	Returns:
		One entry per active row with its ``service_request``, ``customer`` and
		effective ``start`` and ``end``.
	"""
	row = frappe.qb.DocType(ROW_DOCTYPE)
	request = frappe.qb.DocType(USR_DOCTYPE)

	rows = (
		frappe.qb.from_(row)
		.join(request)
		.on(row.parent == request.name)
		.select(
			request.name.as_("service_request"),
			request.customer,
			row.start_date,
			row.end_date,
			request.start_date.as_("request_start"),
			request.end_date.as_("request_end"),
		)
		.where(row.parenttype == USR_DOCTYPE)
		.where(row.utility_property == utility_property)
		.where(row.is_active == 1)
		.where(request.docstatus == 1)
		.where(request.name != (exclude or ""))
	).run(as_dict=True)

	return [
		frappe._dict(
			service_request=entry.service_request,
			customer=entry.customer,
			start=entry.start_date or entry.request_start,
			end=entry.end_date or entry.request_end,
		)
		for entry in rows
	]


def periods_overlap(start, end, other_start, other_end) -> bool:
	"""Return whether two inclusive periods share at least one day.

	A blank start is unbounded and a blank end open ended.
	"""
	if end and other_start and getdate(other_start) > getdate(end):
		return False

	if other_end and start and getdate(start) > getdate(other_end):
		return False

	return True


def describe_period(start, end) -> str:
	"""Describe a lease period for a message."""
	if end:
		return _("from {0} to {1}").format(getdate(start), getdate(end))

	return _("from {0} with no end date").format(getdate(start))
