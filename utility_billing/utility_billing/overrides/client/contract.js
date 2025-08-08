// Copyright (c) 2025, Navari and contributors
// For license information, please see license.txt

frappe.ui.form.on("Contract", {
	refresh: function (frm) {
		frm.fields_dict.properties.grid.cannot_add_rows = true;
		frm.fields_dict["properties"].grid.get_field("utility_property").get_query = function () {
			return {
				filters: {
					status: "Available",
				},
			};
		};

		set_is_active_readonly(frm);
	},
});

frappe.ui.form.on("Contract Utility Property Item", {
	is_active: function (frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (frm.doc.docstatus === 1 && !row.__islocal && row.is_active) {
			frappe.msgprint("You cannot activate a property once the contract is submitted.");
			frappe.model.set_value(cdt, cdn, "is_active", 0);
		}
	},

	form_render: function (frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (frm.doc.docstatus === 1 && !row.is_active) {
			frm.fields_dict.properties.grid.grid_rows_by_docname[cdn].toggle_editable(
				"is_active",
				false
			);
		} else {
			frm.fields_dict.properties.grid.grid_rows_by_docname[cdn].toggle_editable(
				"is_active",
				true
			);
		}
	},
});

function set_is_active_readonly(frm) {
	if (frm.doc.docstatus === 1) {
		(frm.doc.properties || []).forEach((row) => {
			let grid_row = frm.fields_dict.properties.grid.grid_rows_by_docname[row.name];
			if (grid_row) {
				grid_row.toggle_editable("is_active", row.is_active ? true : false);
			}
		});
	}
}
