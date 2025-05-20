// Copyright (c) 2025, Navari Ltd and contributors
// For license information, please see license.txt

frappe.query_reports["Tenancy Summary"] = {
	filters: [
		{
			fieldname: "customer",
			label: __("Customer"),
			fieldtype: "Link",
			options: "Customer",
		},
		{
			fieldname: "property",
			label: __("Property"),
			fieldtype: "Link",
			options: "Utility Property",
		},
		{
			fieldname: "status",
			label: __("Contract Status"),
			fieldtype: "Select",
			options: ["", __("Active"), __("Inactive"), __("Unsigned"), __("Draft")],
			default: "Active",
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
		},
		{
			fieldname: "property_status",
			label: __("Property Tenancy Status"),
			fieldtype: "Select",
			options: ["", __("Active"), __("Inactive")],
		},
	],
};
