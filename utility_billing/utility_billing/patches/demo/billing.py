"""Meter readings and their tariff rates for the demo dataset."""

from collections import defaultdict

import frappe
from frappe.utils import add_days, flt, today

from utility_billing.utility_billing.utils.create_meter_reading_rates import create_meter_reading_rates

from .constants import DEMO_COMPANY, demo_company_names
from .customers import resolve_customer
from .utils import apply_demo_flags, logger, safe_load_json

METER_READING_SAVEPOINT = "demo_meter_reading"


def insert_meter_readings() -> None:
	"""Create the demo meter readings, chaining the readings of each meter.

	A demo entry either describes a single reading or, through ``readings``,
	several readings of the same meters on different dates. Chained readings
	keep each meter increasing: the oldest starts from zero and every later
	reading starts where the previous one ended.

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
				"company": entry.get("company") or DEMO_COMPANY,
				"customer": customer.name,
				"property": entry["property"],
			},
		):
			continue

		for reading in _chain_readings(entry):
			_insert_reading(entry, reading, customer)


def _chain_readings(entry: dict) -> list[dict]:
	"""Return the readings of a demo entry, oldest first, with chained meters.

	The ``consumption`` of a demo item is what its meter measured since the
	previous reading, so the rows are turned into the previous/current pair a
	``Meter Reading`` stores while the meter keeps increasing.
	"""
	rows = entry.get("readings") or [
		{"reading_age_days": entry.get("reading_age_days"), "items": entry.get("items") or []}
	]
	rows = sorted(rows, key=lambda row: -(row.get("reading_age_days") or 0))

	meters: dict[str, float] = defaultdict(float)
	chained = []
	for row in rows:
		items = []
		for item in row.get("items") or []:
			meter = item.get("meter_number") or item["item_code"]
			consumption = flt(item.get("consumption"))
			previous = meters[meter]
			meters[meter] = previous + consumption
			items.append(
				{
					**item,
					"previous_reading": previous,
					"current_reading": previous + consumption,
					"consumption": consumption,
				}
			)
		chained.append({"reading_age_days": row.get("reading_age_days"), "items": items})

	return chained


def _insert_reading(entry: dict, reading: dict, customer) -> None:
	"""Create and submit one reading of a demo entry."""
	date = add_days(today(), -(reading.get("reading_age_days") or 0))

	frappe.db.savepoint(METER_READING_SAVEPOINT)
	try:
		doc = apply_demo_flags(_build_meter_reading(entry, reading, customer, date))
		# The previous reading of a demo meter comes from the chain above, not
		# from billed readings, so validation is skipped and the tariff rates
		# are built from the chained consumption instead.
		doc.flags.ignore_validate = True
		doc.insert()
		create_meter_reading_rates(doc, doc.price_list, doc.date)
		doc.submit()
	except Exception:
		frappe.db.rollback(save_point=METER_READING_SAVEPOINT)
		logger.exception(f"Could not create meter reading for {entry.get('property')} on {date}")


def _build_meter_reading(entry: dict, reading: dict, customer, date):
	"""Build one Meter Reading document from a demo reading row."""
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
			"date": date,
			"price_list": entry["price_list"],
			"currency": entry.get("currency") or "KES",
			"property": entry["property"],
			"warehouse": warehouse,
		}
	)

	for item in reading.get("items") or []:
		item_doc = frappe.get_cached_doc("Item", item["item_code"])
		doc.append(
			"items",
			{
				"item_code": item_doc.name,
				"item_name": item_doc.item_name,
				"uom": item_doc.stock_uom,
				"stock_uom": item_doc.stock_uom,
				"current_reading": item["current_reading"],
				"previous_reading": item["previous_reading"],
				"consumption": item["consumption"],
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
