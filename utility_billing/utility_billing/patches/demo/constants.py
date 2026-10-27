"""Shared constants for the Utility Billing demo dataset."""

import frappe

DEMO_COMPANY = "Utility and Rental (Demo)"
DEMO_PASSWORD = "Demo@12345"
DEMO_EMAIL_DOMAIN = "demo.utilitybilling.test"
PORTAL_ROLE = "Customer"


def demo_company_names() -> list[str]:
	"""Return the demo company and any auto-suffixed copies from older runs."""
	return frappe.get_all(
		"Company",
		filters={"name": ("like", f"{DEMO_COMPANY}%")},
		pluck="name",
		order_by="name asc",
	)
