// Copyright (c) 2024, Navari and contributors
// For license information, please see license.txt

frappe.ui.form.on("Customer", {
	refresh: function (frm) {
		frm.add_custom_button(
			__("Utility Service Request"),
			function () {
				frappe.new_doc("Utility Service Request", {
					customer: frm.doc.name,
				});
			},
			__("Create")
		);
	},
});
