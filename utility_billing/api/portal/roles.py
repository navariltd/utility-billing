"""Portal role and capability resolution for the rental portal.

Portal users are standard Frappe Website Users. Their *portal role* is derived
from the Frappe roles assigned to them together with the ERPNext Customer they
are linked to through the ``Customer.portal_users`` child table:

* ``Tenant``        – Customer role linked to a Customer (see :func:`get_linked_customers`).
* ``Property Owner``/``Landlord``/``Property Manager`` – role based only.
* ``Utility Customer`` – role based only.
* ``Guest``         – anonymous visitor, can only browse properties.

Only the tenant and guest flows are exercised today; the remaining roles are
already resolved here so that later phases can scope their data without
touching this module.
"""

from typing import Iterable, Sequence

import frappe
from frappe.query_builder import DocType
from frappe.utils import cint

GUEST = "Guest"

TENANT_ROLE = "Tenant"
LANDLORD_ROLE = "Property Owner"
LANDLORD_ALIAS = "Landlord"
MANAGER_ROLE = "Property Manager"
UTILITY_CUSTOMER_ROLE = "Utility Customer"
CUSTOMER_ROLE = "Customer"

#: Frappe roles that map onto a portal role, in resolution priority order
#: (most specific first). The value is the resolved portal role.
PORTAL_ROLE_MAP = {
	MANAGER_ROLE: MANAGER_ROLE,
	LANDLORD_ROLE: LANDLORD_ROLE,
	LANDLORD_ALIAS: LANDLORD_ROLE,
	TENANT_ROLE: TENANT_ROLE,
	UTILITY_CUSTOMER_ROLE: UTILITY_CUSTOMER_ROLE,
	CUSTOMER_ROLE: TENANT_ROLE,
}

#: Portal capabilities. Guests may only browse; every authenticated portal user
#: currently receives the full set (role based restrictions land in later phases).
GUEST_CAPABILITIES = ("browse_properties",)

PORTAL_CAPABILITIES = (
	"browse_properties",
	"view_dashboard",
	"view_my_units",
	"manage_profile",
	"manage_notifications",
)


def is_guest(user: str | None = None) -> bool:
	"""Return ``True`` when the given (or current) session user is a Guest."""
	return (user or frappe.session.user) == GUEST


def get_user_roles(user: str | None = None) -> list[str]:
	"""Return the roles of ``user`` (defaults to the current session user)."""
	return frappe.get_roles(user)


def get_linked_customers(user: str | None = None) -> list[dict]:
	"""Return the enabled Customers the given user is linked to.

	The link is the standard ERPNext ``Customer.portal_users`` child table.

	Args:
	    user: User to inspect. Defaults to the current session user.

	Returns:
	    List of dicts with ``name`` and ``customer_name`` keys.
	"""
	user = user or frappe.session.user
	if not user or user == GUEST:
		return []

	portal_user = DocType("Portal User")
	customer = DocType("Customer")

	rows = (
		frappe.qb.from_(portal_user)
		.join(customer)
		.on(portal_user.parent == customer.name)
		.select(customer.name, customer.customer_name, customer.disabled)
		.where((portal_user.parenttype == "Customer") & (portal_user.user == user))
		.run(as_dict=True)
	)

	return [
		{"name": row.name, "customer_name": row.customer_name or row.name}
		for row in rows
		if not cint(row.disabled)
	]


def get_linked_customer(user: str | None = None) -> str | None:
	"""Return the first Customer linked to ``user``, if any."""
	customers = get_linked_customers(user)
	return customers[0]["name"] if customers else None


def resolve_portal_role(roles: Sequence[str], has_linked_customer: bool = False) -> str:
	"""Resolve the portal role from the user's Frappe roles.

	Args:
	    roles: Frappe roles assigned to the user.
	    has_linked_customer: Whether the user is linked to a Customer through
	        ``Customer.portal_users``. Required for tenant style roles.

	Returns:
	    The portal role name, or an empty string when the user is authenticated
	    but does not map to any known portal role.
	"""
	roles = set(roles or ())
	if not roles:
		return GUEST

	for frappe_role, portal_role in PORTAL_ROLE_MAP.items():
		if frappe_role not in roles:
			continue
		if portal_role == TENANT_ROLE and not has_linked_customer:
			continue
		return portal_role

	return ""


def get_portal_capabilities(portal_role: str) -> dict[str, bool]:
	"""Return the capability map for a portal role.

	Args:
	    portal_role: Role resolved by :func:`resolve_portal_role`.

	Returns:
	    Mapping of capability name to boolean.
	"""
	if portal_role == GUEST:
		granted: Iterable[str] = GUEST_CAPABILITIES
	else:
		granted = PORTAL_CAPABILITIES

	granted = set(granted)
	return {capability: capability in granted for capability in PORTAL_CAPABILITIES}


def is_tenant(user: str | None = None) -> bool:
	"""Return ``True`` when the user holds a tenant portal role."""
	if is_guest(user):
		return False

	return resolve_portal_role(get_user_roles(user), bool(get_linked_customers(user))) == TENANT_ROLE


def require_authenticated_user() -> str:
	"""Return the current user, throwing when the request is anonymous.

	Raises:
	    frappe.PermissionError: When the session user is a Guest.
	"""
	if is_guest():
		raise frappe.PermissionError

	return frappe.session.user


def require_tenant() -> str:
	"""Return the current user after asserting tenant portal access.

	Raises:
	    frappe.PermissionError: When the user is a Guest or not a tenant.
	"""
	user = require_authenticated_user()
	if not is_tenant(user):
		frappe.throw(frappe._("You are not linked to any property as a tenant."), frappe.PermissionError)

	return user
