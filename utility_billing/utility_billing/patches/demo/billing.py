"""Meter readings and their tariff rates for the demo dataset."""

import frappe
from frappe.utils import add_days, flt, today

from .constants import DEMO_COMPANY, demo_company_names
from .customers import resolve_customer
from .utils import logger, safe_load_json

METER_READING_SAVEPOINT = "demo_meter_reading"


def insert_meter_readings() -> None:
	"""Create one meter reading per demo property using tiered Item Prices.

	The reading date is relative to today, so the demo remains current however
	long after installation it is generated.
	"""
	readings = safe_load_json("data/meter_reading.json") or []

	for entry in readings:
		customer = resolve_customer(entry["customer"])
		if not customer:
			continue

		if frappe.db.exists(
			"Meter Reading",
			{
				"company": DEMO_COMPANY,
				"customer": customer.name,
				"property": entry["property"],
			},
		):
			continue

		frappe.db.savepoint(METER_READING_SAVEPOINT)
		try:
			doc = _build_meter_reading(entry, customer)
			doc.insert()
			doc.submit()
		except Exception:
			frappe.db.rollback(save_point=METER_READING_SAVEPOINT)
			logger.exception(f"Could not create meter reading for {entry.get('property')}")


def _build_meter_reading(entry: dict, customer):
	"""Build one Meter Reading document from a demo data row."""
	company = entry.get("company") or DEMO_COMPANY
	warehouse = frappe.db.get_value(
		"Warehouse",
		{"company": company, "is_group": 0},
		"name",
		order_by="name asc",
	)
	doc = frappe.get_doc(
		{
			"doctype": "Meter Reading",
			"company": company,
			"customer": customer.name,
			"customer_name": customer.customer_name,
			"territory": customer.territory,
			"date": add_days(today(), -(entry.get("reading_age_days") or 15)),
			"price_list": entry["price_list"],
			"currency": entry.get("currency") or "KES",
			"property": entry["property"],
			"warehouse": warehouse,
		}
	)

	for item in entry.get("items") or []:
		item_doc = frappe.get_cached_doc("Item", item["item_code"])
		consumption = flt(item.get("consumption"))
		doc.append(
			"items",
			{
				"item_code": item_doc.name,
				"item_name": item_doc.item_name,
				"uom": item_doc.stock_uom,
				"stock_uom": item_doc.stock_uom,
				"current_reading": consumption,
				"previous_reading": 0,
				"consumption": consumption,
				"meter_number": item.get("meter_number"),
				"warehouse": warehouse,
			},
		)

	return doc


def delete_sales_orders() -> None:
	"""Cancel and delete the Sales Orders of the demo Customers."""
	from .customers import demo_customer_ids

	demo_customers = demo_customer_ids()
	if not demo_customers:
		return

	orders = frappe.get_all(
		"Sales Order",
		filters={"customer": ("in", demo_customers)},
		fields=["name", "docstatus"],
	)

	for order in orders:
		try:
			auto_repeats = frappe.get_all(
				"Auto Repeat",
				filters={
					"reference_doctype": "Sales Order",
					"reference_document": order.name,
				},
				pluck="name",
			)

			for auto_repeat in auto_repeats:
				auto_repeat_doc = frappe.get_doc("Auto Repeat", auto_repeat)
				if auto_repeat_doc.docstatus == 1:
					auto_repeat_doc.cancel()
				frappe.delete_doc("Auto Repeat", auto_repeat, force=True, ignore_permissions=True)

			if order.docstatus == 1:
				frappe.get_doc("Sales Order", order.name).cancel()

			frappe.delete_doc("Sales Order", order.name, force=True, ignore_permissions=True)
		except Exception:
			logger.exception(f"Error deleting Sales Order {order.name}")


def clear_meter_readings() -> None:
	"""Cancel and delete every Meter Reading of the demo companies."""
	companies = demo_company_names()
	if not companies:
		return

	names = frappe.get_all("Meter Reading", filters={"company": ("in", companies)}, pluck="name")

	for name in names:
		try:
			doc = frappe.get_doc("Meter Reading", name)
			if doc.docstatus == 1:
				doc.cancel()
			frappe.delete_doc("Meter Reading", name, force=True, ignore_permissions=True)
		except Exception:
			logger.exception(f"Failed to delete Meter Reading {name}")
