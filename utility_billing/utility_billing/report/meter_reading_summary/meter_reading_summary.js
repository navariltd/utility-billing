// Copyright (c) 2025, Navari Ltd and contributors
// For license information, please see license.txt

frappe.query_reports["Meter Reading Summary"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.month_start(),
			reqd: 0,
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.month_end(),
			reqd: 0,
		},
		{
			fieldname: "name",
			label: "Meter Reading",
			fieldtype: "Link",
			options: "Meter Reading",
		},
		{
			fieldname: "customer",
			label: __("Customer"),
			fieldtype: "Link",
			options: "Customer",
			reqd: 0,
		},
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 0,
		},
		{
			fieldname: "territory",
			label: __("Territory"),
			fieldtype: "Link",
			options: "Territory",
			reqd: 0,
		},
		{
			fieldname: "item_code",
			label: __("Item"),
			fieldtype: "Link",
			options: "Item",
			reqd: 0,
		},
		{
			fieldname: "meter_number",
			label: __("Meter Number"),
			fieldtype: "Link",
			options: "Serial No",
			reqd: 0,
		},
		{
			fieldname: "utility_property",
			label: __("Property"),
			fieldtype: "Link",
			options: "Utility Property",
			reqd: 0,
		},
	],
};
