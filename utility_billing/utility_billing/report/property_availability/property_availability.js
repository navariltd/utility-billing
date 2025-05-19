// Copyright (c) 2025, Navari Ltd and contributors
// For license information, please see license.txt

frappe.query_reports["Property Availability"] = {
	filters: [
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: [
				"", // For no filter (all)
				"Available",
				"Occupied",
				"Under Maintenance",
				"Reserved",
			],
			default: "",
			reqd: 0,
		},
		{
			fieldname: "utility_category",
			label: __("Utility Category"),
			fieldtype: "Link",
			options: "Utility Category",
			reqd: 0,
		},
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			reqd: 0,
		},
		{
			fieldname: "location",
			label: __("Location"),
			fieldtype: "Data",
			reqd: 0,
		},
		{
			fieldname: "is_fixed_asset",
			label: __("Is Fixed Asset"),
			fieldtype: "Check",
			default: 0,
			reqd: 0,
		},
		{
			fieldname: "min_bedrooms",
			label: __("Minimum Bedrooms"),
			fieldtype: "Int",
			reqd: 0,
		},
		{
			fieldname: "max_bedrooms",
			label: __("Maximum Bedrooms"),
			fieldtype: "Int",
			reqd: 0,
		},
		{
			fieldname: "min_bathrooms",
			label: __("Minimum Bathrooms"),
			fieldtype: "Int",
			reqd: 0,
		},
		{
			fieldname: "max_bathrooms",
			label: __("Maximum Bathrooms"),
			fieldtype: "Int",
			reqd: 0,
		},
		{
			fieldname: "min_unit_size",
			label: __("Minimum Unit Size (sqft)"),
			fieldtype: "Float",
			reqd: 0,
		},
		{
			fieldname: "max_unit_size",
			label: __("Maximum Unit Size (sqft)"),
			fieldtype: "Float",
			reqd: 0,
		},
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			reqd: 0,
		},
	],
	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (column.fieldname === "status") {
			let color_map = {
				Available: "green",
				Occupied: "blue",
				"Under Maintenance": "orange",
				Reserved: "purple",
			};
			let color = color_map[data.status] || "black";
			return `<span style="color: ${color}; font-weight: bold;">${data.status || ""}</span>`;
		}
		return value;
	},
};
