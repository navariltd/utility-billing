"""Utility Bill Structures for the demo company."""

import random

import frappe
from erpnext.accounts.utils import get_fiscal_year
from frappe.utils import today

from .constants import DEMO_COMPANY, demo_company_names
from .utils import apply_demo_flags, safe_load_json


def clear_bill_structures() -> None:
	"""Cancel and delete the demo Utility Bill Structures."""
	companies = demo_company_names()
	if not companies:
		return

	docs = frappe.get_list(
		"Utility Bill Structure",
		filters={"company": ("in", companies)},
		fields=["name"],
	)

	for row in docs:
		try:
			doc = frappe.get_doc("Utility Bill Structure", row.name)
			if doc.docstatus == 1:
				doc.cancel()
			frappe.delete_doc("Utility Bill Structure", row.name, force=True, ignore_permissions=True)
		except Exception:
			frappe.log_error(f"Error deleting {row.name}", "clear_all_bill_structures")


def insert_bill_structures() -> None:
	"""Insert utility bill structures for the current fiscal year."""
	if frappe.db.exists("Utility Bill Structure", {"company": DEMO_COMPANY, "docstatus": 1}):
		return

	bill_structures = safe_load_json("data/utility_bill_structure.json")
	fiscal_year = get_fiscal_year(today(), company=DEMO_COMPANY, raise_on_missing=False, verbose=0)
	fiscal_year_name = fiscal_year[0] if fiscal_year else None

	for structure in bill_structures:
		doc = apply_demo_flags(
			frappe.get_doc(
				{
					"doctype": "Utility Bill Structure",
					"fiscal_year": fiscal_year_name,
					"items": [],
					"company": structure.get("company") or DEMO_COMPANY,
				}
			)
		)

		for item in structure.get("items", []):
			doc.append(
				"items", {"item": item.get("item"), "amount": item.get("amount"), "total": item.get("total")}
			)

		doc.insert()
		doc.submit()


def get_random_bill_structure() -> str | None:
	"""Fetch a random bill structure if available."""
	structures = frappe.get_list(
		"Utility Bill Structure",
		filters={"docstatus": 1},
		fields=["name"],
	)

	if not structures:
		return

	return random.choice(structures).name
