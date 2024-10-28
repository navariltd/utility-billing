// Copyright (c) 2024, Navari and contributors
// For license information, please see license.txt

frappe.ui.form.on("Meter Reading", {
	refresh: function (frm) {
		if (!frm.doc.date) {
			frm.set_value("date", frappe.datetime.now_date());
		}

		frm.fields_dict["items"].grid.get_field("item_code").get_query = function () {
			return {
				filters: {
					is_sales_item: 1,
					is_utility_item: 1,
					has_variants: 0,
				},
			};
		};
	},

	customer: function (frm) {
		if (frm.doc.customer) {
			frappe.call({
				method: "utility_billing.utility_billing.doctype.meter_reading.meter_reading.get_customer_details",
				args: {
					customer: frm.doc.customer,
				},
				callback: function (r) {
					if (r.message) {
						frm.set_value("customer_name", r.message.customer_name);
						frm.set_value("territory", r.message.territory);
						frm.set_value("price_list", r.message.default_price_list);
					}
				},
			});
		}
	},

	items_add: function (frm) {
		frm.doc.items.forEach((item) => {
			if (item.tariff_table && item.tariff_table.length > 0) {
				item.rate = 0;
			}
		});
		frm.refresh_field("items");
	},
	validate: function (frm) {
		frm.doc.items.forEach((item) => {
			if (item.current_reading >= 0 && item.previous_reading >= 0) {
				const consumption = item.current_reading - item.previous_reading;

				if (consumption < 0) {
					frappe.msgprint(
						__("Current reading cannot be lower than previous reading.for item: {0}", [
							item.item_code,
						])
					);
					frappe.validated = false;
				}
			} else {
				frappe.msgprint(
					__(
						"Please ensure that both current and previous readings are provided for item: {0}",
						[item.item_code]
					)
				);
				frappe.validated = false;
			}
		});
	},
});

frappe.ui.form.on("Meter Reading Item", {
	current_reading: function (frm, cdt, cdn) {
		const row = locals[cdt][cdn];

		if (row.previous_reading >= 0 && row.current_reading >= 0) {
			calculate_consumption(frm, row);
		}
	},
	previous_reading: function (frm, cdt, cdn) {
		const row = locals[cdt][cdn];

		if (row.current_reading >= 0 && row.previous_reading >= 0) {
			calculate_consumption(frm, row);
		}
	},
	item_code: function (frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (row.item_code) {
			frappe.call({
				method: "frappe.client.get",
				args: {
					doctype: "Item",
					name: row.item_code,
				},
				callback: function (r) {
					if (r.message) {
						frappe.model.set_value(cdt, cdn, "item_name", r.message.item_name);
						frappe.model.set_value(cdt, cdn, "uom", r.message.stock_uom);
						frappe.model.set_value(cdt, cdn, "stock_uom", r.message.stock_uom);
						frappe.model.set_value(cdt, cdn, "description", r.message.description);

						frappe.call({
							method: "utility_billing.utility_billing.doctype.meter_reading.meter_reading.get_previous_invoice_reading",
							args: {
								item_code: row.item_code,
							},
							callback: function (r) {
								row.previous_reading = r.message[1] || 0;
								frm.refresh_field("items");
							},
						});
					}
				},
			});
		}
	},
});

function calculate_consumption(frm, row) {
	row.consumption = row.current_reading - row.previous_reading;
	if (row.consumption < 0) {
		frappe.msgprint(__("Current reading cannot be lower than previous reading."));
		row.consumption = 0;
		row.current_reading = 0;
	}
	frm.refresh_field("items");
}
