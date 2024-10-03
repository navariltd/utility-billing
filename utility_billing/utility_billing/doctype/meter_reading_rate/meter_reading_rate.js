// Copyright (c) 2024, Navari and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Meter Reading Rate", {
// 	refresh(frm) {

// 	},
// });

frappe.ui.form.on("Meter Reading Item", {
	// Trigger when the Item Code is selected
	item_code: function (frm, cdt, cdn) {
		const row = frappe.get_doc(cdt, cdn);
		if (row.item_code) {
			// Fetch Item Name, Description, UOM, and Stock UOM
			frappe.call({
				method: "frappe.client.get",
				args: {
					doctype: "Item",
					name: row.item_code,
				},
				callback: function (r) {
					if (r.message) {
						frappe.model.set_value(cdt, cdn, "item_name", r.message.item_name);
						frappe.model.set_value(cdt, cdn, "description", r.message.description);
						frappe.model.set_value(cdt, cdn, "uom", r.message.stock_uom);
						frappe.model.set_value(cdt, cdn, "stock_uom", r.message.stock_uom);
					}
				},
			});

			// Fetch Previous Reading for the same item and customer
			frappe.call({
				method: "frappe.client.get_list",
				args: {
					doctype: "Meter Reading Item",
					filters: {
						item_code: row.item_code,
						parent: ["!=", frm.doc.name], // Exclude current doc
						customer: frm.doc.customer,
					},
					fields: ["current_reading"],
					order_by: "creation desc",
					limit: 1,
				},
				callback: function (r) {
					if (r.message && r.message.length > 0) {
						frappe.model.set_value(
							cdt,
							cdn,
							"previous_reading",
							r.message[0].current_reading
						);
					} else {
						frappe.model.set_value(cdt, cdn, "previous_reading", 0); // Default if no previous reading
					}
				},
			});
		}
	},

	// Filter Serial Numbers (Meter Numbers) by Customer
	meter_number: function (frm, cdt, cdn) {
		if (frm.doc.customer) {
			frm.fields_dict["items"].grid.get_field("meter_number").get_query = function () {
				return {
					filters: {
						customer: frm.doc.customer,
					},
				};
			};
		}
	},

	// Auto-calculate consumption when Current Reading changes
	current_reading: function (frm, cdt, cdn) {
		const row = frappe.get_doc(cdt, cdn);
		if (row.current_reading && row.previous_reading) {
			frappe.model.set_value(
				cdt,
				cdn,
				"consumption",
				row.current_reading - row.previous_reading
			);
		}
	},
});
