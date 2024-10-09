// Copyright (c) 2024, Navari and contributors
// For license information, please see license.txt

frappe.ui.form.on("Request for Utility Service", {
	refresh: function (frm) {
		frm.toggle_display("address_html", !frm.is_new());
		if (!frm.is_new()) {
			frappe.contacts.render_address_and_contact(frm);
		}
	},
});
