"""Context and access checks for portal support tickets.

A customer can raise a ticket from a booking or directly from an active tenancy
on the property page. Both flows resolve to the same minimal context: the
Customer, the property, the originating service request (when known) and the
company that owns the ticket.
"""

import frappe
from frappe import _

from utility_billing.api.portal.booking_payload import get_own_request
from utility_billing.api.portal.properties import ACTIVE, get_tenant_properties
from utility_billing.api.portal.roles import get_portal_customers, require_authenticated_user

ISSUE_DOCTYPE = "Issue"


def get_booking_context(booking: str) -> dict:
	"""Return the support context of one of the caller's bookings.

	Raises:
		frappe.PermissionError: When the booking belongs to another Customer.
	"""
	request = get_own_request(booking)
	customer = request.customer or request.party_name
	property_name = first_requested_property(request)

	return {
		"name": request.name,
		"reference": request.name,
		"customer": customer,
		"customer_name": request.customer_name or customer_name(customer),
		"property": property_name,
		"property_name": property_label(property_name),
		"company": request.company,
		"service_request": request.name,
	}


def get_property_context(property: str) -> dict:
	"""Return the support context of a property with an active tenancy.

	Only current allocations (active or reserved) of the caller are accepted;
	historical tenancies cannot raise new tickets.

	Raises:
		frappe.PermissionError: When the property is not actively allocated to the caller.
		frappe.ValidationError: When no property was provided.
		frappe.DoesNotExistError: When the property does not exist.
	"""
	property_name = (property or "").strip()
	if not property_name:
		frappe.throw(_("No property was provided."))

	property_doc = frappe.db.get_value(
		"Utility Property",
		property_name,
		["property_name", "company"],
		as_dict=True,
	)
	if not property_doc:
		frappe.throw(
			_("Property {0} was not found.").format(property_name),
			frappe.DoesNotExistError,
		)

	tenancy = find_current_tenancy(property_name)
	if not tenancy:
		raise frappe.PermissionError

	customers = {customer["name"] for customer in get_portal_customers()}
	contract = frappe.db.get_value(
		"Contract",
		tenancy["contract"],
		["party_name", "utility_service_request"],
		as_dict=True,
	)
	if not contract or contract.party_name not in customers:
		raise frappe.PermissionError

	service_request = contract.utility_service_request or None
	return {
		"name": property_name,
		"reference": tenancy["contract"],
		"customer": contract.party_name,
		"customer_name": customer_name(contract.party_name),
		"property": property_name,
		"property_name": property_doc.property_name or property_name,
		"company": property_doc.company,
		"service_request": service_request,
	}


def get_own_issue(issue: str):
	"""Return an Issue after checking it belongs to the caller.

	Raises:
		frappe.PermissionError: When the ticket is not the caller's.
	"""
	user = require_authenticated_user()
	customers = {customer["name"] for customer in get_portal_customers()}
	doc = frappe.get_doc(ISSUE_DOCTYPE, issue)

	if doc.customer in customers or doc.raised_by == user:
		return doc

	raise frappe.PermissionError


def find_current_tenancy(property_name: str) -> dict | None:
	"""Return the caller's current allocation of a property, if any.

	When a Customer holds both an unsigned reservation and a signed contract for
	the same unit, the active tenancy wins.
	"""
	properties = get_tenant_properties(frappe.session.user)
	matches = [row for row in properties["current"] if row["utility_property"] == property_name]
	if not matches:
		return None

	for row in matches:
		if row["state"] == ACTIVE:
			return row

	return matches[0]


def first_requested_property(request) -> str | None:
	"""Return the first unit requested on a booking."""
	for row in request.get("requested_properties") or []:
		if row.get("utility_property"):
			return row.get("utility_property")

	return None


def property_label(property_name: str | None) -> str | None:
	"""Return the customer-facing label of a property."""
	if not property_name:
		return None

	return frappe.db.get_value("Utility Property", property_name, "property_name") or property_name


def customer_name(customer: str | None) -> str | None:
	"""Return the display name of a Customer."""
	if not customer:
		return None

	return frappe.db.get_value("Customer", customer, "customer_name") or customer
