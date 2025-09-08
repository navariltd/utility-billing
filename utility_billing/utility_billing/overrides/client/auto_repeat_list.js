// Copyright (c) 2025, Navari and contributors
// For license information, please see license.txt

frappe.listview_settings["Auto Repeat"] = {
	onload: function (listview) {
		listview.page.add_action_item(__("Run Selected Auto Repeats"), function () {
			const selected = listview.get_checked_items().map((item) => item.name);
			if (!selected.length) {
				frappe.msgprint(__("Please select at least one Auto Repeat"));
				return;
			}

			frappe.call({
				method: "utility_billing.utility_billing.overrides.server.auto_repeat.create_repeated_entries",
				args: {
					data: selected.map((name) => ({ name })),
				},
				callback: function (r) {
					if (!r.exc) {
						frappe.msgprint(__("Selected Auto Repeats processed successfully"));
						listview.refresh();
					}
				},
			});
		});

		listview.page.add_inner_button(__("Run All Due Auto Repeats"), function () {
			frappe.confirm(__("Are you sure you want to run all due Auto Repeats?"), function () {
				frappe.call({
					method: "utility_billing.utility_billing.overrides.server.auto_repeat.run_all_due_auto_repeats",
					callback: function (r) {
						if (!r.exc) {
							frappe.msgprint(__("All due Auto Repeats processed successfully"));
							listview.refresh();
						}
					},
				});
			});
		});
	},
};
