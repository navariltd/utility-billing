"""Shared building blocks for portal bookings.

A portal booking is a ``Utility Service Request`` that already carries the
customer, the lease dates and the requested properties. Requests created by a
tenant are left as drafts so the property manager can review them before the
lease is committed; allocating the unit happens when that request is submitted.
This module creates those requests and serialises them for the portal, while
:mod:`utility_billing.api.portal.bookings` exposes the public endpoints.
"""

from typing import Any

import frappe
from frappe import _
from frappe.utils import (
	add_months,
	cint,
	flt,
	formatdate,
	getdate,
	nowdate,
	sanitize_html,
	today,
)

from utility_billing.api.portal.properties import PROPERTY_FIELDS
from utility_billing.api.portal.roles import get_portal_customers
from utility_billing.utility_billing.doctype.utility_service_request.utility_service_request import (
	get_service_items_for_properties,
)
from utility_billing.utility_billing.utils.availability import get_live_leases
from utility_billing.utility_billing.utils.price_list import resolve_price_list

REQUEST_DOCTYPE = "Utility Service Request"
SETTINGS_DOCTYPE = "Utility Billing Settings"

DEFAULT_CONTRACT_MONTHS = 12
#: Security deposit shown in the booking summary, expressed in monthly rents.
DEPOSIT_MONTHS = 1

REQUEST_TYPE_CANDIDATES = ("Property Lease", "Tenancy", "Lease")

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
	"owner",
)


def get_booking_customer(customer: str | None = None) -> dict:
	"""Return the Customer the caller books for, provisioning one if needed.

	First-time tenants have no Customer yet; the portal creates and links one
	when none is linked through ``Customer.portal_users`` or their Contact.

	Args:
		customer: Optional Customer the caller selected when linked to several.

	Returns:
		Dict with ``name`` and ``customer_name``.

	Raises:
		frappe.PermissionError: When the caller is not linked to the requested
			Customer.
	"""
	customers = get_portal_customers(create=True)
	if not customers:
		raise frappe.PermissionError

	if not customer:
		return customers[0]

	for entry in customers:
		if entry["name"] == customer:
			return entry

	raise frappe.PermissionError


def resolve_request_type(preferred: str | None = None) -> str:
	"""Return the Issue Type used for tenancy bookings.

	Args:
		preferred: Value already set on the request being extended.

	Returns:
		An existing ``Issue Type`` name.

	Raises:
		frappe.ValidationError: When no Issue Type is configured.
	"""
	if preferred and frappe.db.exists("Issue Type", preferred):
		return preferred

	for candidate in REQUEST_TYPE_CANDIDATES:
		if frappe.db.exists("Issue Type", candidate):
			return candidate

	matches = frappe.db.get_all(
		"Issue Type",
		filters={"name": ("like", "%Lease%")},
		pluck="name",
		limit=1,
	)
	if matches:
		return matches[0]

	first = frappe.db.get_value("Issue Type", {}, "name", order_by="creation asc")
	if first:
		return first

	frappe.throw(
		_(
			"No Issue Type is configured for online bookings. Create a Property Lease "
			"Issue Type before accepting bookings."
		)
	)


def resolve_company(property_doc: dict) -> str:
	"""Return the company a booking is placed under.

	The property company wins; otherwise the site default is used.

	Raises:
		frappe.ValidationError: When no Company exists.
	"""
	company = property_doc.get("company") or frappe.defaults.get_global_default("company")
	if not company:
		company = frappe.db.get_value("Company", {}, "name", order_by="creation asc")

	if not company:
		frappe.throw(_("No Company is configured. Create a Company before accepting bookings."))

	return company


def lease_months(start, end) -> int:
	"""Return the whole months between two dates.

	Matches the calculation used by ``Utility Service Request`` so the portal
	never stores a lease length one month longer than the selected dates.
	"""
	months = (end.year - start.year) * 12 + (end.month - start.month)
	if end.day < start.day:
		months -= 1

	return max(months, 1)


def normalise_dates(
	start_date: str | None,
	end_date: str | None = None,
	contract_length_months: float | int | None = None,
) -> tuple[Any, Any, int]:
	"""Return validated lease dates and their length in months.

	Args:
		start_date: Lease start; defaults to today.
		end_date: Optional lease end.
		contract_length_months: Length used when no end date is given.

	Returns:
		Tuple of ``(start_date, end_date, months)`` as date objects and an int.

	Raises:
		frappe.ValidationError: When the dates are inconsistent or in the past.
	"""
	start = getdate(start_date) if start_date else getdate(today())
	if start < getdate(today()):
		frappe.throw(_("The lease cannot start in the past."))

	if end_date:
		end = getdate(end_date)
		if end <= start:
			frappe.throw(_("The lease end date must be after the start date."))
		months = lease_months(start, end)
	elif contract_length_months:
		months = max(int(flt(contract_length_months)), 1)
		end = add_months(start, months)
	else:
		months = DEFAULT_CONTRACT_MONTHS
		end = add_months(start, months)

	return start, end, months


def get_property_doc(property_name: str) -> dict:
	"""Return the descriptive fields of a bookable property.

	Raises:
		frappe.DoesNotExistError: When the property does not exist.
	"""
	property_doc = frappe.db.get_value(
		"Utility Property",
		property_name,
		[*PROPERTY_FIELDS, "is_group", "service_item", "unique_features", "lot_size"],
		as_dict=True,
	)
	if not property_doc:
		frappe.throw(
			_("Property {0} was not found.").format(frappe.bold(property_name)),
			frappe.DoesNotExistError,
		)

	return property_doc


def assert_bookable(property_doc: dict) -> None:
	"""Raise unless the property is available for a new lease.

	Raises:
		frappe.ValidationError: Naming the reason the unit cannot be booked.
	"""
	if cint(property_doc.get("is_group")):
		frappe.throw(_("Select a unit, not a property group."))

	if property_doc.get("status") != "Available":
		frappe.throw(
			_("Property {0} is not available. Current status: {1}.").format(
				frappe.bold(property_doc.get("property_name") or property_doc.get("name")),
				frappe.bold(property_doc.get("status") or _("Unknown")),
			)
		)

	label = frappe.bold(property_doc.get("property_name") or property_doc.get("name"))
	for lease in get_live_leases(property_names=[property_doc["name"]]):
		if lease["utility_property"] != property_doc["name"] or not lease["is_current"]:
			continue

		if lease["end"]:
			frappe.throw(
				_(
					"Property {0} is already reserved until {1}. Choose another unit "
					"or contact the property manager."
				).format(label, frappe.bold(formatdate(lease["end"])))
			)

		frappe.throw(
			_(
				"Property {0} is already reserved by an open-ended lease. Choose "
				"another unit or contact the property manager."
			).format(label)
		)


def get_pending_booking(customer: str, property_name: str) -> str | None:
	"""Return the caller's draft booking for a property, if one exists.

	Args:
		customer: Customer name the booking belongs to.
		property_name: ``Utility Property`` being reserved.

	Returns:
		Name of the draft ``Utility Service Request``, or ``None``.
	"""
	parents = frappe.db.get_all(
		"Contract Utility Property Item",
		filters={
			"parenttype": REQUEST_DOCTYPE,
			"utility_property": property_name,
			"is_active": 1,
		},
		pluck="parent",
		limit=50,
	)
	if not parents:
		return None

	pending = frappe.db.get_all(
		REQUEST_DOCTYPE,
		filters={
			"name": ("in", parents),
			"customer": customer,
			"docstatus": 0,
		},
		pluck="name",
		order_by="creation desc",
		limit=1,
	)
	return pending[0] if pending else None


def get_booking_options(customer: dict, property_doc: dict) -> dict:
	"""Build the pricing and defaults the booking form starts with.

	Args:
		customer: Customer dict returned by :func:`get_booking_customer`.
		property_doc: ``Utility Property`` fields.

	Returns:
		Monthly rent, deposit, estimated contract value and default dates.
	"""
	price_list = resolve_price_list(customer["name"])
	items = get_service_items_for_properties([property_doc["name"]], price_list)
	monthly_rent = flt(items[0]["rate"]) if items else 0.0
	currency = frappe.db.get_value(
		"Company", resolve_company(property_doc), "default_currency"
	) or frappe.db.get_value("Currency", {}, "name")

	start = getdate(today())
	return {
		"customer": customer,
		"property": property_doc,
		"price_list": price_list,
		"currency": currency,
		"monthly_rent": monthly_rent,
		"deposit_amount": monthly_rent * DEPOSIT_MONTHS,
		"deposit_months": DEPOSIT_MONTHS,
		"estimated_total": monthly_rent * DEFAULT_CONTRACT_MONTHS,
		"default_start_date": str(start),
		"default_end_date": str(add_months(start, DEFAULT_CONTRACT_MONTHS)),
		"default_contract_length_months": DEFAULT_CONTRACT_MONTHS,
		"service_item": items[0]["item_code"] if items else None,
	}


def create_booking_request(
	customer: dict,
	property_doc: dict,
	start_date,
	end_date,
	contract_length_months: int,
	*,
	notes: str | None = None,
	nrcpassport_no: str | None = None,
	request_type: str | None = None,
	price_list: str | None = None,
	submit: bool = True,
) -> Any:
	"""Create the Utility Service Request of a booking.

	Args:
		customer: Customer dict returned by :func:`get_booking_customer`.
		property_doc: Bookable ``Utility Property`` fields.
		start_date: Lease start date.
		end_date: Lease end date.
		contract_length_months: Lease length in months.
		notes: Free text saved in ``remarks``.
		nrcpassport_no: Tenant identity number.
		request_type: Issue Type; resolved when omitted.
		price_list: Price list used to price the rent item.
		submit: Submit the request immediately. Portal bookings pass ``False``
			so the manager reviews the lease before it is committed.

	Returns:
		The inserted ``Utility Service Request`` document.
	"""
	settings = frappe.get_cached_doc(SETTINGS_DOCTYPE)
	price_list = price_list or resolve_price_list(customer["name"])
	items = get_service_items_for_properties([property_doc["name"]], price_list)
	if not items:
		frappe.throw(
			_(
				"Property {0} has no billable rent item. Configure its service item "
				"before accepting online bookings."
			).format(frappe.bold(property_doc.get("property_name") or property_doc["name"]))
		)

	item = items[0]
	billing_approach = settings.rent_billing_approach or None

	request = frappe.new_doc(REQUEST_DOCTYPE)
	request.update(
		{
			"date": nowdate(),
			"company": resolve_company(property_doc),
			"customer": customer["name"],
			"customer_name": customer["customer_name"],
			"service_request_from": "Customer",
			"party_name": customer["name"],
			"request_type": resolve_request_type(request_type),
			"utility_property": property_doc["name"],
			"start_date": start_date,
			"end_date": end_date,
			"contract_length_months": contract_length_months,
			"price_list": price_list,
			"nrcpassport_no": nrcpassport_no,
			"remarks": sanitize_html(notes) if notes else None,
		}
	)

	request.append(
		"requested_properties",
		{
			"utility_property": property_doc["name"],
			"item_code": item["item_code"],
			"start_date": start_date,
			"end_date": end_date,
			"is_active": 1,
			"contract_length_months": contract_length_months,
			"enable_auto_billing": 1 if billing_approach else 0,
			"rent_billing_approach": billing_approach,
			"billing_date_type": "First Day of Month" if billing_approach == "Item Price" else None,
			"billing_day_of_month": getdate(start_date).day if billing_approach == "Item Price" else None,
		},
	)

	item_fields = {field.fieldname for field in frappe.get_meta("Utility Service Request Item").fields}
	item_row = {key: value for key, value in item.items() if key in item_fields}
	item_row.update(
		{
			"qty": item_row.get("qty") or 1,
			"delivery_date": start_date,
			"amount": flt(item_row.get("rate")) * flt(item_row.get("qty") or 1),
		}
	)
	request.append("items", item_row)

	request.flags.ignore_permissions = True
	request.insert()
	if submit:
		request.submit()

	return request
