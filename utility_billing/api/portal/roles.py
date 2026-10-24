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

from collections.abc import Iterable, Sequence

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


def get_portal_customers(user: str | None = None, *, create: bool = False) -> list[dict]:
	"""Return the Customers that represent ``user`` in the portal.

	Resolves ``Customer.portal_users`` first, then the Customer linked to the
	user's Contact. When neither exists and ``create`` is true, a Customer is
	provisioned for the user so a first-time tenant can book without admin
	involvement.

	Args:
		user: User to inspect. Defaults to the current session user.
		create: Whether a missing Customer may be created.

	Returns:
		List of dicts with ``name`` and ``customer_name`` keys.
	"""
	user = user or frappe.session.user
	if not user or user == GUEST:
		return []

	customers = get_linked_customers(user)
	if customers:
		return customers

	contact_customer = get_contact_customer(user)
	if contact_customer:
		return [contact_customer]

	if not create:
		return []

	return [create_customer_for_user(user)]


def get_contact_customer(user: str) -> dict | None:
	"""Return the Customer linked to the user's Contact through its email."""
	email = frappe.db.get_value("User", user, "email") or user
	contact = frappe.db.get_value(
		"Contact Email",
		{"email_id": email, "parenttype": "Contact"},
		"parent",
		order_by="creation asc",
	)
	if not contact:
		return None

	customer = frappe.db.get_value(
		"Dynamic Link",
		{"parent": contact, "parenttype": "Contact", "link_doctype": "Customer"},
		"link_name",
	)
	if not customer:
		return None

	customer_name = frappe.db.get_value("Customer", {"name": customer, "disabled": 0}, "customer_name")
	if not customer_name:
		return None

	return {"name": customer, "customer_name": customer_name}


def create_customer_for_user(user: str) -> dict:
	"""Create a Customer for a portal user and link it to their login.

	The portal provisions the Customer itself, so the insert ignores the
	caller's permissions; the user is appended to ``portal_users`` in the same
	document.

	Args:
		user: Login of the portal user.

	Returns:
		Dict with ``name`` and ``customer_name`` of the Customer.
	"""
	user_doc = frappe.get_cached_doc("User", user)
	email = user_doc.email or user

	existing = frappe.db.get_value(
		"Customer", {"email_id": email, "disabled": 0}, ["name", "customer_name"], as_dict=True
	)
	if existing:
		link_customer_user(existing.name, user)
		return {"name": existing.name, "customer_name": existing.customer_name or existing.name}

	customer_name = (user_doc.full_name or user.split("@")[0]).strip() or email
	customer = frappe.new_doc("Customer")
	customer.update(
		{
			"customer_name": customer_name,
			"customer_type": "Individual",
			"customer_group": default_customer_group(),
			"territory": default_territory(),
			"email_id": email,
			"mobile_no": user_doc.mobile_no or user_doc.phone,
			"portal_users": [{"user": user}],
		}
	)
	customer.flags.ignore_permissions = True
	customer.insert()

	return {"name": customer.name, "customer_name": customer.customer_name}


def link_customer_user(customer: str, user: str) -> None:
	"""Append ``user`` to the Customer's portal users when not linked yet."""
	if frappe.db.exists("Portal User", {"parenttype": "Customer", "parent": customer, "user": user}):
		return

	customer_doc = frappe.get_doc("Customer", customer)
	customer_doc.append("portal_users", {"user": user})
	customer_doc.flags.ignore_permissions = True
	customer_doc.save()


def default_customer_group() -> str:
	"""Return a leaf Customer Group for portal-provisioned Customers.

	Raises:
		frappe.ValidationError: When no leaf Customer Group exists.
	"""
	group = frappe.db.get_default("customer_group")
	if group and not cint(frappe.db.get_value("Customer Group", group, "is_group")):
		return group

	group = frappe.db.get_value("Customer Group", {"is_group": 0}, "name", order_by="lft asc")
	if not group:
		frappe.throw(frappe._("Create a Customer Group before accepting portal sign-ups."))

	return group


def default_territory() -> str:
	"""Return a leaf Territory for portal-provisioned Customers.

	Raises:
		frappe.ValidationError: When no leaf Territory exists.
	"""
	territory = frappe.db.get_default("territory")
	if territory and not cint(frappe.db.get_value("Territory", territory, "is_group")):
		return territory

	territory = frappe.db.get_value("Territory", {"is_group": 0}, "name", order_by="lft asc")
	if not territory:
		frappe.throw(frappe._("Create a Territory before accepting portal sign-ups."))

	return territory


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
