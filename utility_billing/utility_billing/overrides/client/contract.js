// Copyright (c) 2025, Navari and contributors
// For license information, please see license.txt

frappe.ui.form.on("Contract", {
	refresh: function (frm) {
		frm.fields_dict["properties"].grid.get_field("utility_property").get_query = function () {
			return {
				filters: {
					status: "Available",
				},
			};
		};
	},
});
