"""Session bootstrap for the rental portal single page application.

The SPA receives the standard Frappe session boot (including ``frappe.boot.user.roles``)
with the ``/rental-portal`` page. This endpoint adds the portal specific context
that the framework cannot derive on its own: the resolved portal role, the
Customer the user is linked to and the capabilities granted to that role.

Everything returned here is scoped to the session user; no user data is accepted
from the client.
"""

import frappe

from utility_billing.api.portal.roles import (
	GUEST,
	get_linked_customers,
	get_portal_capabilities,
	get_user_roles,
	resolve_portal_role,
)

USER_FIELDS = ("full_name", "email", "user_image", "language", "time_zone")


@frappe.whitelist(allow_guest=True)
def get_portal_context() -> dict:
	"""Return the portal context for the current session user.

	Returns:
	    A dict containing the user identity, Frappe roles, resolved portal role,
	    linked Customer(s) and the capability map driving the portal navigation.
	"""
	user = frappe.session.user
	if user == GUEST:
		return _guest_context()

	profile = frappe.db.get_value("User", user, USER_FIELDS, as_dict=True) or frappe._dict()
	roles = get_user_roles(user)
	customers = get_linked_customers(user)
	portal_role = resolve_portal_role(roles, bool(customers))

	return {
		"user": user,
		"full_name": profile.get("full_name") or user,
		"email": profile.get("email"),
		"user_image": profile.get("user_image"),
		"language": profile.get("language"),
		"time_zone": profile.get("time_zone"),
		"roles": roles,
		"portal_role": portal_role,
		"customer": customers[0]["name"] if customers else None,
		"customers": customers,
		"capabilities": get_portal_capabilities(portal_role),
	}


def _guest_context() -> dict:
	"""Return the portal context handed to anonymous visitors."""
	return {
		"user": GUEST,
		"full_name": GUEST,
		"email": None,
		"user_image": None,
		"language": frappe.local.lang,
		"time_zone": None,
		"roles": [GUEST],
		"portal_role": GUEST,
		"customer": None,
		"customers": [],
		"capabilities": get_portal_capabilities(GUEST),
	}
