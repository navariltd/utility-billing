import json

import frappe

from .utils import safe_load_json


def insert_meter_readings() -> None:
	readings = safe_load_json("data/meter_reading.json")
	for entry in readings:
		meter_reading_name = frappe.db.get_value(
			"Meter Reading",
			filters={"customer": entry["customer"], "date": entry["date"], "property": entry["property"]},
			fieldname="name",
		)

		if meter_reading_name:
			doc = frappe.get_doc("Meter Reading", meter_reading_name)
			doc.update(
				{
					"price_list": entry["price_list"],
					"currency": entry["currency"],
					"company": entry["company"],
				}
			)
		else:
			doc = frappe.get_doc(
				{
					"doctype": "Meter Reading",
					"customer": entry["customer"],
					"date": entry["date"],
					"price_list": entry["price_list"],
					"currency": entry["currency"],
					"property": entry["property"],
					"company": entry["company"],
				}
			)

		doc.set("items", [])

		for item in entry.get("items", []):
			doc.append(
				"items",
				{
					"item_code": item["item_code"],
					"current_reading": item["current_reading"],
					"previous_reading": item["previous_reading"],
					"consumption": item["consumption"],
					"meter_number": item["meter_number"],
				},
			)

		doc.save()
		doc.submit()


def delete_sales_orders() -> None:
	customers_data = safe_load_json("data/customer.json")
	demo_customers = [c["customer_name"] for c in customers_data]
	if not demo_customers:
		return

	demo_sales_orders = {
		so.name: so
		for so in frappe.get_all(
			"Sales Order",
			filters={"customer": ["in", demo_customers]},
			fields=["name", "docstatus", "customer"],
		)
	}

	if not demo_sales_orders:
		return

	deleted_count = 0
	for so_name, so in demo_sales_orders.items():
		try:
			auto_repeats = frappe.get_all(
				"Auto Repeat",
				filters={"reference_doctype": "Sales Order", "reference_document": so_name},
				fields=["name"],
			)

			for ar in auto_repeats:
				try:
					ar_doc = frappe.get_doc("Auto Repeat", ar.name)
					if ar_doc.docstatus == 1:
						ar_doc.cancel()
					frappe.delete_doc("Auto Repeat", ar.name)
				except Exception as e:
					frappe.db.rollback()
					frappe.log_error(f"Error handling Auto Repeat for Sales Order {so_name}: {e}")

			if so.docstatus == 1:
				frappe.get_doc("Sales Order", so_name).cancel()

			frappe.delete_doc("Sales Order", so_name)
			frappe.db.commit()
			deleted_count += 1

		except Exception as e:
			frappe.db.rollback()
			frappe.log_error(f"Error deleting Sales Order {so_name}: {e}")


def clear_meter_readings() -> None:
	readings = safe_load_json("data/meter_reading.json")

	for entry in readings:
		meter_reading_name = frappe.db.get_value(
			"Meter Reading",
			filters={"customer": entry["customer"], "date": entry["date"], "property": entry["property"]},
			fieldname="name",
		)

		if not meter_reading_name:
			continue

		try:
			doc = frappe.get_doc("Meter Reading", meter_reading_name)

			# Match items
			json_items = sorted(
				[
					{
						"item_code": item["item_code"],
						"current_reading": item["current_reading"],
						"previous_reading": item["previous_reading"],
						"consumption": item["consumption"],
						"meter_number": item["meter_number"],
					}
					for item in entry.get("items", [])
				],
				key=lambda x: (x["item_code"], x["meter_number"]),
			)

			doc_items = sorted(
				[
					{
						"item_code": i.item_code,
						"current_reading": i.current_reading,
						"previous_reading": i.previous_reading,
						"consumption": i.consumption,
						"meter_number": i.meter_number,
					}
					for i in doc.items
				],
				key=lambda x: (x["item_code"], x["meter_number"]),
			)

			if json_items != doc_items:
				continue

			if doc.docstatus == 1:
				doc.cancel()
			doc.delete()

			frappe.db.commit()

		except Exception as e:
			frappe.log_error(
				f"Failed to delete Meter Reading {meter_reading_name}: {str(e)}", "Meter Reading Deletion"
			)
