// Copyright (c) 2025, Navari Ltd and contributors
// For license information, please see license.txt

frappe.query_reports["Tenancy Summary"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
		},
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
			options: [
				"",
				__("Active"),
				__("Nearing End"),
				__("Inactive"),
				__("Unsigned"),
				__("Draft"),
			],
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

	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (column.fieldname === "status") {
			let color_map = {
				Active: "#28a745",
				"Nearing End": "#ffa500",
				Expired: "#6c757d",
				Cancelled: "#dc3545",
				Draft: "#007bff",
			};
			let color = color_map[data.status] || "black";
			return `<span style="color: ${color}; font-weight: bold;">${data.status || ""}</span>`;
		}
		return value;
	},
};
