"""Release Utility Properties whose lease has ended.

A property is set back to Available by the Contract ``on_update_after_submit``
hook, but ERPNext's daily ``update_status_for_contracts`` moves a Contract to
Inactive with a direct database write, so that hook never runs and the property
stays Occupied or Reserved. This daily job reads the lease from the submitted
Utility Service Requests instead: the dates on a Contract are a copy taken when
it was made and can go stale, while the request stays current.
"""

from collections import defaultdict

import frappe
from frappe.utils import getdate, today

from .item_price_scope import property_contract_period

HELD_STATUSES = ("Occupied", "Reserved")
LEASE_DOCTYPE = "Contract Utility Property Item"
REQUEST_DOCTYPE = "Utility Service Request"


def release_ended_leases() -> list[str]:
	"""Set held properties whose every lease has ended back to Available.

	A property can be leased by several submitted requests over time, a renewal
	for instance, so it is released only when all of its active leases ended
	before today. A lease without an end date never ends, and a lease that has
	not started yet still holds the property. A property without any submitted
	lease is left alone, since there is no end date to judge it by.

	Returns:
		Names of the properties set back to Available.
	"""
	held = frappe.get_all(
		"Utility Property",
		filters={"is_group": 0, "status": ("in", HELD_STATUSES)},
		pluck="name",
	)
	if not held:
		return []

	lease_ends = get_lease_ends(held)
	current_date = getdate(today())
	released = []

	for property_name, ends in lease_ends.items():
		if all(end and getdate(end) < current_date for end in ends):
			frappe.db.set_value("Utility Property", property_name, "status", "Available")
			released.append(property_name)

	return released


def get_lease_ends(property_names: list[str]) -> dict[str, list]:
	"""Return the end date of every active lease of the given properties.

	Args:
		property_names: ``Utility Property`` names.

	Returns:
		The lease end dates of each property, ``None`` for an open ended lease.
		Properties without a submitted lease are left out.
	"""
	lease = frappe.qb.DocType(LEASE_DOCTYPE)
	request = frappe.qb.DocType(REQUEST_DOCTYPE)
	rows = (
		frappe.qb.from_(lease)
		.join(request)
		.on(request.name == lease.parent)
		.select(lease.parent, lease.utility_property)
		.where(lease.parenttype == REQUEST_DOCTYPE)
		.where(lease.utility_property.isin(property_names))
		.where(lease.is_active == 1)
		.where(request.docstatus == 1)
		.distinct()
		.run(as_dict=True)
	)

	lease_ends = defaultdict(list)
	for row in rows:
		service_request = frappe.get_doc(REQUEST_DOCTYPE, row.parent)
		lease_ends[row.utility_property].append(
			property_contract_period(service_request, row.utility_property)[1]
		)

	return lease_ends
