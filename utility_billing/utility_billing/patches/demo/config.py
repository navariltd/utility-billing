"""Settings required by the Utility Billing demo dataset.

The demo keeps the site's recurring billing approach untouched. It only fills
configuration that the generated records need: a default price list, a service
item group and item price UOM, and the service item auto-creation flag.
"""

import frappe

SETTINGS_DOCTYPE = "Utility Billing Settings"
DEMO_PRICE_LISTS = ("Standard Residential", "Standard Commercial")


def ensure_demo_price_lists() -> None:
	"""Create or enable the selling Price Lists used by the demo.

	ERPNext only accepts a Customer's default price list when it is a selling
	price list. The lists are ensured before the Customer master data is read,
	because a Customer references its default list while it is inserted.
	"""
	for name in DEMO_PRICE_LISTS:
		if frappe.db.exists("Price List", name):
			price_list = frappe.get_doc("Price List", name)
		else:
			price_list = frappe.new_doc("Price List")
			price_list.price_list_name = name

		price_list.currency = "KES"
		price_list.selling = 1
		price_list.enabled = 1
		price_list.flags.ignore_permissions = True
		price_list.save()


def configure_demo_settings() -> None:
	"""Apply the minimum Utility Billing Settings needed by the demo.

	Existing values are preserved. ``rent_billing_approach`` is deliberately
	not changed, so the demo follows the site's configured Auto Repeat or
	Item Price approach.
	"""
	settings = frappe.get_doc(SETTINGS_DOCTYPE)

	defaults = {
		"default_price_list": ("Price List", "Standard Residential"),
		"default_service_item_group": ("Item Group", "Utilities"),
		"default_item_price_uom": ("UOM", "Nos"),
	}

	changed = False
	for fieldname, (doctype, value) in defaults.items():
		if not settings.get(fieldname) and frappe.db.exists(doctype, value):
			settings.set(fieldname, value)
			changed = True

	if not settings.auto_create_service_item:
		settings.auto_create_service_item = 1
		changed = True

	if changed:
		settings.save(ignore_permissions=True)

	ensure_auto_repeat_doctype()


def ensure_auto_repeat_doctype() -> None:
	"""Enable Auto Repeat on Sales Invoice when the demo uses that approach.

	The app ships the same change as the ``set_allow_auto_repeat_sales_invoice``
	patch. Re-applying it here keeps demo generation working on sites where the
	patch has not run yet.
	"""
	settings = frappe.get_cached_doc(SETTINGS_DOCTYPE)
	if settings.rent_billing_approach != "Auto Repeat":
		return

	if frappe.get_meta("Sales Invoice").allow_auto_repeat:
		return

	frappe.db.set_value("DocType", "Sales Invoice", "allow_auto_repeat", 1)
	frappe.clear_cache(doctype="Sales Invoice")
