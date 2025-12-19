# Copyright (c) 2025, Navari Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	summary = get_report_summary(data)
	chart = get_chart_data(data)
	return columns, data, None, chart, summary


def get_columns():
	return [
		{
			"label": _("Property"),
			"fieldname": "property_name",
			"fieldtype": "Link",
			"options": "Utility Property",
			"width": 200,
		},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 120},
		{
			"label": _("Location"),
			"fieldname": "location",
			"fieldtype": "Link",
			"options": "Location",
			"width": 180,
		},
		{
			"label": _("Utility Category"),
			"fieldname": "utility_category",
			"fieldtype": "Link",
			"options": "Utility Category",
			"width": 150,
		},
		{
			"label": _("Company"),
			"fieldname": "company",
			"fieldtype": "Link",
			"options": "Company",
			"width": 150,
		},
		{"label": _("Is Fixed Asset"), "fieldname": "is_fixed_asset", "fieldtype": "Check", "width": 100},
		{
			"label": _("Gross Purchase Amount"),
			"fieldname": "gross_purchase_amount",
			"fieldtype": "Currency",
			"width": 140,
		},
		{"label": _("Unit Number"), "fieldname": "unit_number", "fieldtype": "Data", "width": 120},
		{"label": _("Bedrooms"), "fieldname": "bedrooms", "fieldtype": "Int", "width": 100},
		{"label": _("Bathrooms"), "fieldname": "bathrooms", "fieldtype": "Int", "width": 100},
		{"label": _("Unit Size (sqft)"), "fieldname": "unit_size", "fieldtype": "Float", "width": 120},
		{
			"label": _("Floor Level"),
			"fieldname": "floor_level",
			"fieldtype": "Link",
			"options": "Floor Level",
			"width": 120,
		},
	]


def get_data(filters):
	filters = filters or {}
	conditions = {"is_group": 0}

	exact_filters = ["status", "utility_category", "company", "is_fixed_asset"]
	for key in exact_filters:
		if key in filters and filters[key] not in [None, ""]:
			conditions[key] = filters[key]

	if filters.get("location"):
		conditions["location"] = ["like", f"%{filters['location']}%"]

	range_fields = ["bedrooms", "bathrooms", "unit_size"]
	for field in range_fields:
		min_key = f"min_{field}"
		max_key = f"max_{field}"

		if filters.get(min_key) is not None and filters.get(min_key) != "":
			conditions[field] = [">=", filters[min_key]]

		if filters.get(max_key) is not None and filters.get(max_key) != "":
			conditions[field] = ["<=", filters[max_key]]

	props = frappe.get_all(
		"Utility Property",
		filters=conditions,
		fields=[
			"property_name",
			"status",
			"location",
			"utility_category",
			"company",
			"is_fixed_asset",
			"gross_purchase_amount",
			"unit_number",
			"bedrooms",
			"bathrooms",
			"unit_size",
			"floor_level",
			"modified",
		],
	)
	return props


def get_report_summary(data):
	total_properties = len(data)
	total_value = sum(d.get("gross_purchase_amount", 0) or 0 for d in data)
	available_units = sum(1 for d in data if d.get("status") == "Available")

	return [
		{"label": "Total Properties", "value": total_properties, "indicator": "blue"},
		{"label": "Available Units", "value": available_units, "indicator": "green"},
		{"label": "Total Asset Value", "value": f"KES {total_value:,.2f}", "indicator": "orange"},
	]


def get_chart_data(data):
	status_counts = {}
	for d in data:
		status = d.get("status") or "No Status"
		status_counts[status] = status_counts.get(status, 0) + 1

	labels = list(status_counts.keys())
	values = list(status_counts.values())

	color_map = {
		"Available": "green",
		"Occupied": "blue",
		"Under Maintenance": "orange",
		"Reserved": "purple",
	}

	colors = [color_map.get(label, "#808080") for label in labels]

	return {
		"data": {"labels": labels, "datasets": [{"name": "Properties", "values": values}]},
		"type": "pie",
		"colors": colors,
	}
