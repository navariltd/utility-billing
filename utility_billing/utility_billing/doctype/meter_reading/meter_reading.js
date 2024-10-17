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
});

frappe.ui.form.on("Meter Reading Item", {
	meter_number: function (frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (row.meter_number) {
			frappe.call({
				method: "utility_billing.utility_billing.doctype.meter_reading.meter_reading.get_previous_reading",
				args: {
					meter_number: row.meter_number,
				},
				callback: function (r) {
					row.previous_reading = r.message || 0;
					frm.refresh_field("items");
				},
			});
		}
	},

	current_reading: function (frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (row.previous_reading !== undefined || row.previous_reading !== 0) {
			row.consumption = row.current_reading - row.previous_reading;
			frm.refresh_field("items");
		}
	},
	previous_reading: function (frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (row.current_reading !== undefined || row.current_reading !== 0) {
			row.consumption = row.current_reading - row.previous_reading;
			frm.refresh_field("items");
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

						frm.refresh_field("items");
					}
				},
			});
		}
	},
});
