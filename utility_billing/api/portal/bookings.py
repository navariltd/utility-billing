"""Portal unit bookings.

A booking records the tenant's Customer, the chosen lease dates and a
``requested_properties`` row on a ``Utility Service Request``. Portal bookings
are created as drafts so the property manager can review them; submitting the
request is what allocates the unit and starts the Contract. The request is the
booking record: its reference, notes, status and history all come from the
request and the Contract made from it.
"""

import frappe
from frappe import _

from utility_billing.api.portal.booking_actions import (
	cancel_booking,
	extend_booking,
	modify_booking,
)
from utility_billing.api.portal.booking_core import (
	assert_bookable,
	create_booking_request,
	get_booking_customer,
	get_pending_booking,
	get_property_doc,
	normalise_dates,
)
from utility_billing.api.portal.booking_core import (
	get_booking_options as build_booking_options,
)
from utility_billing.api.portal.booking_payload import (
	get_own_request,
	get_request_rows,
	serialise_doc,
	serialise_many,
	serialise_one,
)
from utility_billing.api.portal.notifications import notify_booking_event
from utility_billing.api.portal.permissions import ignore_permissions
from utility_billing.api.portal.roles import get_portal_customers
from utility_billing.utility_billing.utils.lease_status import CURRENT_STATUSES, DRAFT

__all__ = [
	"cancel_booking",
	"create_booking",
	"extend_booking",
	"get_booking",
	"get_booking_options",
	"get_my_bookings",
	"modify_booking",
]

REQUEST_DOCTYPE = "Utility Service Request"
REQUEST_FIELDS = (
	"name",
	"date",
	"start_date",
	"end_date",
	"contract_length_months",
	"remarks",
	"docstatus",
	"customer",
	"customer_name",
	"company",
	"request_type",
	"request_status",
	"nrcpassport_no",
	"creation",
	"modified",
	"utility_property",
)


@frappe.whitelist()
def get_booking_options(property: str) -> dict:
	"""Return the property, pricing and defaults for the booking form.

	Args:
		property: ``Utility Property`` name.

	Returns:
		Customer, property, monthly rent, deposit, default dates and the
		tenant's pending request for the unit, when one exists.

	Raises:
		frappe.ValidationError: When the unit is not available.
		frappe.PermissionError: When the caller is anonymous.
	"""
	property_doc = get_property_doc(property)
	assert_bookable(property_doc)
	customer = get_booking_customer()
	options = build_booking_options(customer, property_doc)
	options["pending_booking"] = get_pending_booking(customer["name"], property_doc["name"])
	return options


@frappe.whitelist()
def create_booking(
	property: str,
	start_date: str | None = None,
	end_date: str | None = None,
	contract_length_months: float | None = None,
	notes: str | None = None,
	nrcpassport_no: str | None = None,
	customer: str | None = None,
) -> dict:
	"""Create a booking request for the manager to review.

	The ``Utility Service Request`` is inserted as a draft: the unit stays
	available until staff submit the request. A tenant with an existing draft
	request for the same unit is sent back to that request instead of creating
	a duplicate.

	Args:
		property: ``Utility Property`` name.
		start_date: Lease start; defaults to today.
		end_date: Lease end; derived from the length when omitted.
		contract_length_months: Lease length when no end date is given.
		notes: Booking notes saved on the request.
		nrcpassport_no: Tenant identity number.
		customer: Customer to book for, when the user is linked to several.

	Returns:
		The serialised draft booking.

	Raises:
		frappe.ValidationError: When the unit is unavailable, the dates clash, or
			the tenant already has a pending request for the unit.
		frappe.PermissionError: When the caller cannot book for the Customer.
	"""
	property_doc = get_property_doc(property)
	assert_bookable(property_doc)
	booking_customer = get_booking_customer(customer)
	start, end, months = normalise_dates(start_date, end_date, contract_length_months)

	pending = get_pending_booking(booking_customer["name"], property_doc["name"])
	if pending:
		frappe.throw(
			_(
				"You already have a pending booking request for {0}. Track it in "
				"My Bookings or cancel it before booking again."
			).format(frappe.bold(property_doc.get("property_name") or property_doc["name"]))
		)

	with ignore_permissions():
		request = create_booking_request(
			booking_customer,
			property_doc,
			start,
			end,
			months,
			notes=notes,
			nrcpassport_no=nrcpassport_no,
			submit=False,
		)

		notify_booking_event(
			frappe.session.user,
			"requested",
			request,
			end_date=frappe.utils.formatdate(end),
		)
		booking = serialise_one(request.name)[0]

	return booking


@frappe.whitelist()
def get_my_bookings() -> dict:
	"""Return the caller's current and past bookings."""
	customers = get_portal_customers()
	if not customers:
		return {"customer": None, "current": [], "history": [], "counts": {"current": 0, "history": 0}}

	names = [customer["name"] for customer in customers]
	requests = frappe.db.get_all(
		REQUEST_DOCTYPE,
		filters={"customer": ("in", names)},
		fields=list(REQUEST_FIELDS),
		order_by="creation desc",
		limit=200,
	)

	rows_by_request = get_request_rows(request.name for request in requests)
	requests = [request for request in requests if rows_by_request.get(request.name)]
	bookings = serialise_many(requests, names, rows_by_request)

	current = [
		booking
		for booking in bookings
		if booking["lease_status"] in (*CURRENT_STATUSES, DRAFT)
	]
	history = [
		booking
		for booking in bookings
		if booking["lease_status"] not in (*CURRENT_STATUSES, DRAFT)
	]

	return {
		"customer": customers[0]["name"],
		"current": current,
		"history": history,
		"counts": {"current": len(current), "history": len(history)},
	}


@frappe.whitelist()
def get_booking(name: str) -> dict:
	"""Return one of the caller's bookings with its activity timeline.

	Args:
		name: ``Utility Service Request`` name.

	Returns:
		Dict with ``booking`` and ``timeline``.

	Raises:
		frappe.PermissionError: When the booking belongs to another Customer.
	"""
	request = get_own_request(name)
	booking, timeline = serialise_doc(request)
	return {"booking": booking, "timeline": timeline}
