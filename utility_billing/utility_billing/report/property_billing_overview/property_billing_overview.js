// Copyright (c) 2025, Navari Ltd and contributors
// For license information, please see license.txt

frappe.query_reports["Property Billing Overview"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			reqd: 1,
			default: frappe.defaults.get_user_default("Company"),
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(
				frappe.datetime.get_today(),
				-1,
			),
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{
			fieldname: "property",
			label: __("Property"),
			fieldtype: "Link",
			options: "Utility Property",
		},
		{
			fieldname: "customer",
			label: __("Customer"),
			fieldtype: "Link",
			options: "Customer",
		},
		{
			fieldname: "show_property_fields",
			label: __("Show Property Details"),
			fieldtype: "Check",
			default: 0,
		},
		{
			fieldname: "show_totals",
			label: __("Show Totals"),
			fieldtype: "Check",
			default: 1,
		},
	],
};
