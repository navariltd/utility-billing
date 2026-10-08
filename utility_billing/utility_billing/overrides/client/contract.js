// Copyright (c) 2025, Navari and contributors
// For license information, please see license.txt

// Copied from the Utility Service Request, never edited on the Contract; Is Active stays editable
const LOCKED_ROW_FIELDS = [
	"utility_property",
	"item_code",
	"start_date",
	"end_date",
	"contract_length_months",
	"adjustment_rule",
	"insurance",
];

frappe.ui.form.on("Contract", {
	refresh: function (frm) {
		lock_properties(frm);
		set_is_active_readonly(frm);
	},
});

// Child handlers are shared by every form with this child table, including the
// Utility Service Request, so each one returns early outside a Contract.
frappe.ui.form.on("Contract Utility Property Item", {
	is_active: function (frm, cdt, cdn) {
		if (frm.doctype !== "Contract") return;

		let row = locals[cdt][cdn];
		if (frm.doc.docstatus === 1 && !row.__islocal && row.is_active) {
			frappe.msgprint("You cannot activate a property once the contract is submitted.");
			frappe.model.set_value(cdt, cdn, "is_active", 0);
		}
	},

	form_render: function (frm, cdt, cdn) {
		if (frm.doctype !== "Contract") return;

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

// The rows and the request link come from the Utility Service Request through
// create_contract. Only this form's docfields change, so the request's own
// table stays editable.
function lock_properties(frm) {
	const grid = frm.fields_dict.properties.grid;

	frm.set_df_property("utility_service_request", "read_only", 1);
	// Booleans, not 1: the grid passes these to jQuery toggleClass, which toggles on a number
	frm.set_df_property("properties", "cannot_add_rows", true);
	frm.set_df_property("properties", "cannot_delete_rows", true);
	LOCKED_ROW_FIELDS.forEach((fieldname) => grid.update_docfield_property(fieldname, "read_only", 1));

	// The grid is drawn before refresh runs, so redraw it to hide Add and Delete
	frm.refresh_field("properties");
}

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
