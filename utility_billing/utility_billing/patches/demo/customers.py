"""Resolution of demo Customer references.

The demo data files use human readable names, while ERPNext names Customer
records with its own series (for example ``C00001``). These helpers translate a
display name to the actual Customer document and list the demo Customers.
"""

import frappe
from frappe.model.document import Document

from .utils import safe_load_json

CUSTOMER_FILE = "data/customer.json"


def resolve_customer(reference: str | None) -> Document | None:
	"""Return a Customer by document name or by ``customer_name``."""
	if not reference:
		return None

	if frappe.db.exists("Customer", reference):
		return frappe.get_cached_doc("Customer", reference)

	name = frappe.db.get_value("Customer", {"customer_name": reference}, "name")
	return frappe.get_cached_doc("Customer", name) if name else None


def resolve_customer_name(reference: str | None) -> str | None:
	"""Return the document name of a Customer reference, if it exists."""
	customer = resolve_customer(reference)
	return customer.name if customer else None


def demo_customer_ids() -> list[str]:
	"""Return the document names of all demo Customers."""
	names = []
	for row in safe_load_json(CUSTOMER_FILE) or []:
		name = resolve_customer_name(row.get("customer_name"))
		if name:
			names.append(name)

	return names
