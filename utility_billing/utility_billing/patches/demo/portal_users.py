"""Portal Users for the demo tenants.

Each demo Customer gets a Website User linked through ``Customer.portal_users``
so the rental portal resolves the user as a Tenant. All demo accounts share the
documented demonstration password and use the reserved ``.test`` email domain.
"""

import frappe
from frappe.model.document import Document

from .constants import DEMO_PASSWORD, PORTAL_ROLE
from .customers import resolve_customer
from .utils import logger, safe_load_json

PORTAL_USER_FILE = "data/portal_user.json"


def create_portal_users() -> None:
	"""Create the demo Website Users and link them to their Customers."""
	records = safe_load_json(PORTAL_USER_FILE) or []

	for record in records:
		try:
			user = _upsert_user(record)
			_link_customer(record["customer"], user.name)
		except Exception:
			logger.exception(f"Could not create demo portal user {record.get('email')}")


def delete_demo_portal_users() -> None:
	"""Unlink and delete every User created for the demo dataset."""
	records = safe_load_json(PORTAL_USER_FILE) or []

	for record in records:
		email = record.get("email")
		if not email:
			continue

		try:
			_unlink_customer(record.get("customer"), email)
			if frappe.db.exists("User", email):
				frappe.delete_doc("User", email, force=True, ignore_permissions=True)
		except Exception:
			logger.exception(f"Could not delete demo portal user {email}")


def get_demo_user_email(customer: str | None) -> str | None:
	"""Return the demo portal email linked to ``customer``, if any."""
	if not customer:
		return None

	for record in safe_load_json(PORTAL_USER_FILE) or []:
		if record.get("customer") == customer:
			return record.get("email")

	return None


def _upsert_user(record: dict) -> Document:
	"""Create or update the Website User of a demo portal account."""
	email = (record.get("email") or "").strip().lower()
	if not email:
		raise ValueError("A demo portal user needs an email address.")

	full_name = (record.get("full_name") or email).strip()
	first_name, last_name = _split_name(full_name)
	is_new = not frappe.db.exists("User", email)

	user = frappe.new_doc("User") if is_new else frappe.get_doc("User", email)
	user.update(
		{
			"email": email,
			"first_name": first_name,
			"last_name": last_name,
			"enabled": 1,
			"user_type": "Website User",
			"send_welcome_email": 0,
		}
	)

	if is_new:
		user.new_password = DEMO_PASSWORD

	if frappe.db.exists("Role", PORTAL_ROLE) and PORTAL_ROLE not in {
		row.role for row in user.get("roles") or []
	}:
		user.append("roles", {"role": PORTAL_ROLE})

	user.flags.ignore_permissions = True
	user.save()
	return user


def _link_customer(customer: str, user: str) -> None:
	"""Add the portal User to ``Customer.portal_users`` when missing."""
	customer_doc = resolve_customer(customer)
	if not customer_doc:
		return

	if any(row.user == user for row in customer_doc.get("portal_users") or []):
		return

	customer_doc.append("portal_users", {"user": user})
	customer_doc.flags.ignore_permissions = True
	customer_doc.save()


def _unlink_customer(customer: str | None, user: str) -> None:
	"""Remove a portal User link from its Customer before the User is deleted."""
	customer_doc = resolve_customer(customer)
	if not customer_doc:
		return

	remaining = [row for row in customer_doc.get("portal_users") or [] if row.user != user]
	if len(remaining) == len(customer_doc.get("portal_users") or []):
		return

	customer_doc.set("portal_users", remaining)
	customer_doc.flags.ignore_permissions = True
	customer_doc.save()


def _split_name(full_name: str) -> tuple[str, str | None]:
	"""Split a display name into Frappe's first and last name fields."""
	parts = full_name.split()
	if len(parts) == 1:
		return parts[0], None

	return parts[0], " ".join(parts[1:])
