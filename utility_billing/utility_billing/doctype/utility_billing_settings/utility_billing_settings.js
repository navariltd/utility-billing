// Copyright (c) 2024, Navari and contributors
// For license information, please see license.txt

frappe.ui.form.on("Utility Billing Settings", {
	refresh(frm) {
		// Add any initialization logic if needed
	},

	generate_demo_data(frm) {
		frappe.call({
			method: "frappe.client.get_value",
			args: {
				doctype: "Company",
				filters: { name: "Utility and Rental (Demo)" },
				fieldname: "name",
			},
			callback: function (r) {
				if (r.message && r.message.name) {
					frappe.msgprint({
						title: __("Demo Exists"),
						message: __(
							"Demo setup already exists. Cannot generate data again.",
						),
						indicator: "red",
					});
				} else {
					proceed_with_generate();
				}
			},
		});

		function proceed_with_generate() {
			frappe.confirm(
				__(
					"Are you sure you want to generate utility billing and property management demo data?",
				),
				() => {
					frappe.call({
						method: "utility_billing.setup.demo.setup_demo_data",
						freeze: true,
						freeze_message: __(
							"Generating utility billing and property management demo data...",
						),
						callback: function (r) {
							frappe.show_alert({
								message: __(
									"Utility billing and property management demo data successfully generated",
								),
								indicator: "green",
							});
						},
					});
				},
			);
		}
	},

	clear_demo_data(frm) {
		frappe.call({
			method: "frappe.client.get_value",
			args: {
				doctype: "Company",
				filters: { name: "Utility and Rental (Demo)" },
				fieldname: "name",
			},
			callback: function (r) {
				if (!r.message || !r.message.name) {
					frappe.msgprint({
						title: __("Demo Setup Not Found"),
						message: __(
							"Demo data does not exist. Nothing to clear.",
						),
						indicator: "orange",
					});
				} else {
					proceed_with_clear();
				}
			},
		});

		function proceed_with_clear() {
			frappe.confirm(
				__(
					"Are you sure you want to clear all utility billing and property management demo data?",
				),
				() => {
					frappe.call({
						method: "utility_billing.setup.demo.clear_demo_data",
						freeze: true,
						freeze_message: __(
							"Clearing utility billing and property management demo data...",
						),
						callback: function (r) {
							frappe.show_alert({
								message: __(
									"Utility billing and property management demo data successfully cleared",
								),
								indicator: "green",
							});
						},
					});
				},
			);
		}
	},
});
