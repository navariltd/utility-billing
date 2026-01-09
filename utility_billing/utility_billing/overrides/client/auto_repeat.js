// Copyright (c) 2025, Navari and contributors
// For license information, please see license.txt

frappe.ui.form.on("Auto Repeat", {
	refresh: function (frm) {
		if (!frm.doc.next_schedule_date || frm.doc.disabled) return;

		let today = frappe.datetime.get_today();
		if (frm.doc.next_schedule_date <= today) {
			frm.add_custom_button(__("Create Now"), function () {
				frappe.call({
					method: "utility_billing.utility_billing.overrides.server.auto_repeat.create_repeated_entries",
					args: {
						data: [{ name: frm.doc.name }],
					},
					callback: function (r) {
						if (!r.exc) {
							frappe.msgprint(
								__("Documents created successfully"),
							);
							frm.reload_doc();
						}
					},
				});
			});
		}
	},
});
