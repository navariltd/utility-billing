"""Cleanup of records generated outside the demo master data files.

Property service items and their generated Item Prices are created on demand,
so they are not part of ``utility_demo_master_doctypes``. These helpers remove
them without touching items or prices belonging to other data.
"""

import frappe

from .utils import logger, safe_load_json

RENT_FILE = "data/property_rent.json"
AUTO_REPEAT_DOCTYPES = ("Sales Invoice", "Sales Order")


def delete_demo_auto_repeats() -> None:
	"""Delete Auto Repeats pointing at documents of the demo Customers.

	Called before the transactions are deleted, while the reference documents
	still exist and can be traced back to their Customer.
	"""
	from .customers import demo_customer_ids

	customers = set(demo_customer_ids())
	if not customers:
		return

	auto_repeats = frappe.get_all(
		"Auto Repeat",
		filters={"reference_doctype": ("in", AUTO_REPEAT_DOCTYPES)},
		fields=["name", "reference_doctype", "reference_document"],
	)

	for row in auto_repeats:
		customer = frappe.db.get_value(row.reference_doctype, row.reference_document, "customer")
		if customer in customers:
			frappe.delete_doc("Auto Repeat", row.name, force=True, ignore_permissions=True)


def delete_demo_property_item_prices() -> None:
	"""Delete Item Prices of the generated property service items."""
	item_codes = _demo_property_items()
	if not item_codes:
		return

	names = frappe.get_all("Item Price", filters={"item_code": ("in", item_codes)}, pluck="name")
	for name in names:
		frappe.delete_doc("Item Price", name, force=True, ignore_permissions=True)


def delete_demo_property_service_items() -> None:
	"""Delete the service items named after demo properties.

	Run after the properties themselves have been deleted, so no property still
	references the item.
	"""
	for item_code in _demo_property_items():
		if not frappe.db.exists("Item", item_code):
			continue

		try:
			frappe.delete_doc("Item", item_code, force=True, ignore_permissions=True)
		except Exception:
			logger.exception(f"Could not delete demo service item {item_code}")


def _demo_property_items() -> list[str]:
	"""Return the item codes derived from the demo property names."""
	return [row["property_name"] for row in safe_load_json(RENT_FILE) or [] if row.get("property_name")]
