// Copyright (c) 2024, Navari and contributors
// For license information, please see license.txt

frappe.ui.form.on("Meter Reading", {
	// Trigger when the form is loaded or refreshed
	onload: function (frm) {
		// Auto-fill the Date field with the current date if it's empty
		if (!frm.doc.date) {
			frm.set_value("date", frappe.datetime.now_date());
		}
	},

	// Trigger when the Customer is selected
	customer: function (frm) {
		if (frm.doc.customer) {
			// Fetch Customer Name
			frappe.db.get_value("Customer", frm.doc.customer, "customer_name", (r) => {
				frm.set_value("customer_name", r.customer_name);
			});

			// Fetch Price List (from customer or customer group)
			frappe.db.get_value("Customer", frm.doc.customer, "default_price_list", (r) => {
				if (r.default_price_list) {
					frm.set_value("price_list", r.default_price_list);
				} else {
					// If no price list on customer, check customer group
					frappe.db.get_value(
						"Customer Group",
						frm.doc.customer_group,
						"default_price_list",
						(r) => {
							frm.set_value("price_list", r.default_price_list);
						}
					);
				}
			});
		}
	},
});
