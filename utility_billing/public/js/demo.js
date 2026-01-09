frappe.provide("utility_billing.demo");

$(document).on("toolbar_setup", function () {
	if (!frappe.user.has_role("System Manager")) {
		return;
	}
	frappe.call({
		method: "frappe.client.get_value",
		args: {
			doctype: "Company",
			filters: { name: "Utility and Rental (Demo)" },
			fieldname: "name",
		},
		callback: function (r) {
			if (r.message && r.message.name) {
				render_clear_utility_billing_demo_action();
			} else {
				render_generate_utility_billing_demo_action();
			}
		},
	});
});

function render_generate_utility_billing_demo_action() {
	let demo_action = $(
		`<a class="dropdown-item" onclick="return utility_billing.demo.generate_demo_data()">
            ${__("Generate Utility & Rental Demo Data")}
        </a>`,
	);
	demo_action.appendTo($("#toolbar-user"));
}

function render_clear_utility_billing_demo_action() {
	let demo_action = $(
		`<a class="dropdown-item" onclick="return utility_billing.demo.clear_demo_data()">
            ${__("Clear Utility & Rental Demo Data")}
        </a>`,
	);
	demo_action.appendTo($("#toolbar-user"));
}

utility_billing.demo.generate_demo_data = function () {
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
				frappe.ui.toolbar.clear_cache();
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
						frappe.ui.toolbar.clear_cache();
					},
				});
			},
		);
	}
};

utility_billing.demo.clear_demo_data = function () {
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
					message: __("Demo data does not exist. Nothing to clear."),
					indicator: "orange",
				});
				frappe.ui.toolbar.clear_cache();
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
						frappe.ui.toolbar.clear_cache();
					},
				});
			},
		);
	}
};
