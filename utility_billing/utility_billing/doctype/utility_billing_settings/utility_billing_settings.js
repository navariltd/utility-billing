// Copyright (c) 2024, Navari and contributors
// For license information, please see license.txt

frappe.ui.form.on("Utility Billing Settings", {
	generate_demo_data(frm) {
		frappe.confirm(
			__(
				"Are you sure you want to generate utility billing and property management demo data?"
			),
			() => {
				frappe.call({
					method: "utility_billing.setup.demo.setup_demo_data",
					freeze: true,
					freeze_message: __(
						"Generating utility billing and property management demo data..."
					),
					callback: function (r) {
						frappe.show_alert({
							message: __(
								"Utility billing and property management demo data successfully generated"
							),
							indicator: "green",
						});
					},
				});
			}
		);
	},

	clear_demo_data(frm) {
		frappe.confirm(
			__(
				"Are you sure you want to clear all utility billing and property management demo data?"
			),
			() => {
				frappe.call({
					method: "utility_billing.setup.demo.clear_demo_data",
					freeze: true,
					freeze_message: __(
						"Clearing utility billing and property management demo data..."
					),
					callback: function (r) {
						frappe.show_alert({
							message: __(
								"Utility billing and property management demo data successfully cleared"
							),
							indicator: "green",
						});
					},
				});
			}
		);
	},
});
