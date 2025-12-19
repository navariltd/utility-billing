import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})
	data = get_data(filters)
	return get_columns(), data, None, get_chart_data(data), get_report_summary(data)


def get_columns():
	return [
		{
			"label": _("Meter Reading"),
			"fieldname": "name",
			"fieldtype": "Dynamic Link",
			"options": "Meter Reading",
			"width": 250,
			"indent": 0,
		},
		{"label": _("Type"), "fieldname": "type", "fieldtype": "Data", "hidden": 1, "width": 100},
		{"label": _("Date"), "fieldname": "date", "fieldtype": "Date", "width": 100},
		{
			"label": _("Customer"),
			"fieldname": "customer",
			"fieldtype": "Link",
			"options": "Customer",
			"width": 120,
		},
		{
			"label": _("Property"),
			"fieldname": "utility_property",
			"fieldtype": "Link",
			"options": "Utility Property",
			"width": 120,
		},
		{
			"label": _("Company"),
			"fieldname": "company",
			"fieldtype": "Link",
			"options": "Company",
			"width": 100,
		},
		{
			"label": _("Meter Number"),
			"fieldname": "meter_number",
			"fieldtype": "Link",
			"options": "Serial No",
			"width": 120,
		},
		{"label": _("Item"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 120},
		{
			"label": _("Previous Reading"),
			"fieldname": "previous_reading",
			"fieldtype": "Float",
			"width": 120,
			"precision": 3,
		},
		{
			"label": _("Current Reading"),
			"fieldname": "current_reading",
			"fieldtype": "Float",
			"width": 120,
			"precision": 3,
		},
		{
			"label": _("Consumption"),
			"fieldname": "consumption",
			"fieldtype": "Float",
			"width": 120,
			"precision": 3,
		},
		{
			"label": _("Block"),
			"fieldname": "block",
			"fieldtype": "Link",
			"options": "Utility Tariff Block",
			"width": 120,
		},
		{"label": _("Quantity"), "fieldname": "qty", "fieldtype": "Float", "width": 80, "precision": 3},
		{
			"label": _("Rate"),
			"fieldname": "rate",
			"fieldtype": "Currency",
			"width": 100,
			"options": "currency",
		},
		{
			"label": _("Amount"),
			"fieldname": "amount",
			"fieldtype": "Currency",
			"width": 120,
			"options": "currency",
		},
	]


def get_data(filters):
	conditions = {"docstatus": 1}

	if filters.get("from_date") and filters.get("to_date"):
		conditions["date"] = ["between", [filters["from_date"], filters["to_date"]]]
	else:
		if filters.get("from_date"):
			conditions["date"] = [">=", filters["from_date"]]
		if filters.get("to_date"):
			conditions["date"] = ["<=", filters["to_date"]]

	for key in ("customer", "utility_property", "company", "name"):
		if filters.get(key):
			conditions[key] = filters[key]

	readings = frappe.get_all(
		"Meter Reading",
		filters=conditions,
		fields=[
			"name",
			"date",
			"customer",
			"utility_property",
			"company",
			"currency",
		],
		order_by="date desc, customer",
	)

	data = []

	for reading in readings:
		item_filters = {"parent": reading.name}
		for key in ("item_code", "meter_number"):
			if filters.get(key):
				item_filters[key] = filters[key]

		items = frappe.get_all(
			"Meter Reading Item",
			filters=item_filters,
			fields=[
				"name",
				"item_code",
				"meter_number",
				"previous_reading",
				"current_reading",
				"consumption",
			],
		)

		reading_printed = False

		for item in items:
			rates = frappe.get_all(
				"Meter Reading Tariff Rate",
				filters={"parent": reading.name, "meter_reading_item": item.name},
				fields=["name", "block", "qty", "rate", "amount"],
			)

			if rates:
				for i, rate in enumerate(rates):
					data.append(
						{
							"name": reading.name if not reading_printed and i == 0 else "",
							"type": "Rate",
							"date": reading.date if not reading_printed and i == 0 else "",
							"customer": reading.customer if not reading_printed and i == 0 else "",
							"utility_property": reading.utility_property
							if not reading_printed and i == 0
							else "",
							"company": reading.company if not reading_printed and i == 0 else "",
							"meter_number": item.meter_number if i == 0 else "",
							"item_code": item.item_code if i == 0 else "",
							"previous_reading": item.previous_reading
							if not reading_printed and i == 0
							else "",
							"current_reading": item.current_reading if not reading_printed and i == 0 else "",
							"consumption": item.consumption if not reading_printed and i == 0 else "",
							"block": rate.block,
							"qty": rate.qty,
							"rate": rate.rate,
							"amount": rate.amount,
							"currency": reading.currency,
							"indent": 1,
						}
					)
				reading_printed = True
			else:
				data.append(
					{
						"name": reading.name if not reading_printed else "",
						"type": "Item",
						"date": reading.date if not reading_printed else "",
						"customer": reading.customer if not reading_printed else "",
						"utility_property": reading.utility_property if not reading_printed else "",
						"company": reading.company if not reading_printed else "",
						"meter_number": item.meter_number,
						"item_code": item.item_code,
						"previous_reading": item.previous_reading,
						"current_reading": item.current_reading,
						"consumption": item.consumption,
						"currency": reading.currency,
						"indent": 1,
					}
				)
				reading_printed = True

	return data


def get_chart_data(data):
	if not data:
		return None

	consumption_data = {}
	for row in data:
		if row.get("type") in ("Item", "Rate"):
			item_code = row.get("item_code")
			consumption_data[item_code] = consumption_data.get(item_code, 0) + (row.get("consumption") or 0)

	return {
		"data": {
			"labels": list(consumption_data.keys()),
			"datasets": [{"name": _("Total Consumption"), "values": list(consumption_data.values())}],
		},
		"type": "bar",
		"title": _("Consumption by Item"),
		"height": 300,
		"colors": ["#7CD6FD", "#743EE2", "#FF5858", "#FFC744"],
	}


def get_report_summary(data):
	if not data:
		return []

	total_readings = len(set(row.get("name") for row in data if row.get("name")))
	total_consumption = sum(row.get("consumption", 0) for row in data if row.get("consumption"))
	total_amount = sum(row.get("amount", 0) for row in data if row.get("amount"))
	currency = next(
		(row.get("currency") for row in data if row.get("currency")),
		frappe.get_cached_value("Company", frappe.defaults.get_user_default("company"), "default_currency"),
	)

	return [
		{"value": total_readings, "label": _("Total Readings"), "datatype": "Int", "indicator": "Blue"},
		{
			"value": total_consumption,
			"label": _("Total Consumption"),
			"datatype": "Float",
			"precision": 2,
			"indicator": "Green",
		},
		{
			"value": total_amount,
			"label": _("Total Amount"),
			"datatype": "Currency",
			"indicator": "Orange",
			"currency": currency,
		},
	]
