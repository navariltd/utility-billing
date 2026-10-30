"""Portal Users for the demo tenants.

A single demo Customer gets a Website User linked through
``Customer.portal_users`` so the rental portal resolves the user as a Tenant.
That Customer also owns the largest slice of the dataset (several leases,
meter readings and support tickets), so the portal has meaningful data to
show. The demo account uses the documented demonstration password and the
reserved ``.test`` email domain.
"""

import frappe
from frappe.model.document import Document

from .constants import DEMO_EMAIL_DOMAIN, DEMO_PASSWORD, PORTAL_ROLE
from .customers import resolve_customer
from .utils import apply_demo_flags, logger, safe_load_json

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
	"""Unlink and delete every User created for the demo dataset.

	The lookup also matches the reserved demo email domain, so Users left
	behind by earlier demo runs (when every Customer had a portal account)
	are removed as well.
	"""
	for email in _demo_portal_emails():
		try:
			for customer in _linked_customers(email):
				_unlink_customer(customer, email)
			if frappe.db.exists("User", email):
				frappe.delete_doc("User", email, force=True, ignore_permissions=True)
		except Exception:
			logger.exception(f"Could not delete demo portal user {email}")


def _demo_portal_emails() -> set[str]:
	"""Return the demo portal emails of this dataset and of earlier runs.

	Earlier datasets also used sub-domains (``finance@company.demo...``), so the
	lookup matches the reserved domain wherever it appears in the email.
	"""
	emails = {
		record["email"].strip().lower()
		for record in safe_load_json(PORTAL_USER_FILE) or []
		if record.get("email")
	}
	emails.update(
		frappe.get_all(
			"User",
			filters={"name": ("like", f"%{DEMO_EMAIL_DOMAIN}")},
			pluck="name",
		)
	)
	return emails


def _linked_customers(email: str) -> list[str]:
	"""Return the Customers whose ``portal_users`` table links the User."""
	return frappe.get_all(
		"Portal User",
		filters={"user": email, "parenttype": "Customer"},
		pluck="parent",
		distinct=True,
	)


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

	apply_demo_flags(user).save()
	return user


def _link_customer(customer: str, user: str) -> None:
	"""Add the portal User to ``Customer.portal_users`` when missing."""
	customer_doc = resolve_customer(customer)
	if not customer_doc:
		return

	if any(row.user == user for row in customer_doc.get("portal_users") or []):
		return

	customer_doc.append("portal_users", {"user": user})
	apply_demo_flags(customer_doc).save()


def _unlink_customer(customer: str | None, user: str) -> None:
	"""Remove a portal User link from its Customer before the User is deleted."""
	customer_doc = resolve_customer(customer)
	if not customer_doc:
		return

	remaining = [row for row in customer_doc.get("portal_users") or [] if row.user != user]
	if len(remaining) == len(customer_doc.get("portal_users") or []):
		return

	customer_doc.set("portal_users", remaining)
	apply_demo_flags(customer_doc).save()


def _split_name(full_name: str) -> tuple[str, str | None]:
	"""Split a display name into Frappe's first and last name fields."""
	parts = full_name.split()
	if len(parts) == 1:
		return parts[0], None

	return parts[0], " ".join(parts[1:])
