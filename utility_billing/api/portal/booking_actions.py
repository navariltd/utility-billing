"""Booking changes available to a tenant from the portal.

Modification and cancellation are only possible before a Contract exists; once
the Contract pins the lease dates, an extension becomes a renewal request.
"""

import frappe
from frappe import _
from frappe.utils import add_days, add_months, cint, getdate, today

from utility_billing.api.portal.booking_core import (
	create_booking_request,
	get_booking_customer,
	get_property_doc,
	lease_months,
	normalise_dates,
)
from utility_billing.api.portal.booking_payload import (
	add_booking_comment,
	ensure_modifiable,
	get_own_request,
	serialise_one,
)
from utility_billing.api.portal.notifications import notify_booking_event
from utility_billing.utility_billing.utils.lease_status import CANCELLED, get_contracts_by_request


@frappe.whitelist()
def modify_booking(
	name: str,
	start_date: str | None = None,
	end_date: str | None = None,
	contract_length_months: float | None = None,
	notes: str | None = None,
) -> dict:
	"""Change the dates or notes of a booking that has no Contract yet."""
	request = get_own_request(name)
	ensure_modifiable(request)

	if start_date or end_date or contract_length_months:
		start, end, months = normalise_dates(
			start_date or request.start_date,
			end_date,
			contract_length_months or request.contract_length_months,
		)
		request.start_date = start
		request.end_date = end
		request.contract_length_months = months
		for row in request.requested_properties:
			row.start_date = start
			row.end_date = end
			row.contract_length_months = months

	if notes is not None:
		request.remarks = frappe.utils.sanitize_html(notes)

	request.flags.ignore_permissions = True
	request.save()

	add_booking_comment(name, _("The tenant changed the booking dates."))
	notify_booking_event(
		frappe.session.user,
		"modified",
		request,
		end_date=frappe.utils.formatdate(request.end_date),
	)
	return serialise_one(name)[0]


@frappe.whitelist()
def cancel_booking(name: str, reason: str | None = None) -> dict:
	"""Cancel a booking that has no Contract yet.

	Draft (pending) bookings are deleted so they leave no orphan request;
	submitted requests are cancelled and keep their history.

	Args:
		name: ``Utility Service Request`` name.
		reason: Optional note appended to the request history.

	Returns:
		The serialised cancelled booking.
	"""
	request = get_own_request(name)
	ensure_modifiable(request)

	if cint(request.docstatus) == 0:
		booking = serialise_one(name)[0]
		request.flags.ignore_permissions = True
		request.delete()
		booking.update(
			{
				"docstatus": 2,
				"lease_status": CANCELLED,
				"can_modify": False,
				"can_cancel": False,
				"can_extend": False,
				"can_pay": False,
			}
		)
		return booking

	comment = _("The tenant cancelled the booking.")
	if reason:
		comment = f"{comment} {frappe.utils.sanitize_html(reason)}"

	request.flags.ignore_permissions = True
	request.cancel()
	add_booking_comment(name, comment)
	notify_booking_event(frappe.session.user, "cancelled", request)
	return serialise_one(name)[0]


@frappe.whitelist()
def extend_booking(
	name: str,
	contract_length_months: float | None = None,
	end_date: str | None = None,
	notes: str | None = None,
) -> dict:
	"""Extend a booking, or create its renewal once a Contract exists.

	Without a Contract the request's end date is moved. With a Contract the
	lease dates are locked, so a follow-on request starts the day after the
	current lease ends.
	"""
	request = get_own_request(name)
	if cint(request.docstatus) != 1:
		frappe.throw(_("Only a confirmed booking can be extended."))

	contract = get_contracts_by_request([name]).get(name)
	if not contract:
		return _extend_request(request, contract_length_months, end_date)

	if not request.end_date:
		frappe.throw(_("An open ended booking cannot be renewed. Set an end date first."))

	new_start = add_days(getdate(request.end_date), 1)
	if end_date:
		new_end = getdate(end_date)
	elif contract_length_months:
		new_end = add_months(new_start, int(contract_length_months))
	else:
		frappe.throw(_("Provide the number of months or the new end date."))

	if new_end <= new_start:
		frappe.throw(_("The renewal end date must be after {0}.").format(new_start))

	row = request.requested_properties[0]
	property_doc = get_property_doc(row.utility_property)
	booking_customer = get_booking_customer(request.customer)
	months = lease_months(new_start, new_end)

	renewal = create_booking_request(
		booking_customer,
		property_doc,
		new_start,
		new_end,
		months,
		notes=notes,
		request_type=request.request_type,
		price_list=request.price_list,
	)

	add_booking_comment(
		name,
		_("Renewal {0} created for {1} to {2}.").format(
			renewal.name, frappe.utils.formatdate(new_start), frappe.utils.formatdate(new_end)
		),
	)
	notify_booking_event(
		frappe.session.user,
		"renewed",
		renewal,
		end_date=frappe.utils.formatdate(new_end),
	)

	booking = serialise_one(renewal.name)[0]
	booking["renewal_of"] = name
	return booking


def _extend_request(request, contract_length_months: float | None, end_date: str | None) -> dict:
	"""Move the end date of a request that has no Contract yet."""
	current_end = getdate(request.end_date) if request.end_date else None
	if end_date:
		new_end = getdate(end_date)
	elif contract_length_months:
		new_end = add_months(current_end or getdate(today()), int(contract_length_months))
	else:
		frappe.throw(_("Provide the number of months or the new end date."))

	if current_end and new_end <= current_end:
		frappe.throw(_("The new end date must be after {0}.").format(current_end))

	months = lease_months(getdate(request.start_date), new_end)
	request.end_date = new_end
	request.contract_length_months = months
	for row in request.requested_properties:
		row.end_date = new_end
		row.contract_length_months = months

	request.flags.ignore_permissions = True
	request.save()

	add_booking_comment(
		request.name,
		_("The tenant extended the booking to {0}.").format(frappe.utils.formatdate(new_end)),
	)
	notify_booking_event(
		frappe.session.user,
		"extended",
		request,
		end_date=frappe.utils.formatdate(new_end),
	)
	return serialise_one(request.name)[0]
