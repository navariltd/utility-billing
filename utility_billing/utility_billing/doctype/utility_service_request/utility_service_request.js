// Copyright (c) 2024, Navari and contributors
// For license information, please see license.txt

frappe.ui.form.on("Utility Service Request", {
	refresh: function (frm) {
		frm.toggle_display("address_html", !frm.is_new());
		if (!frm.is_new()) {
			frappe.contacts.render_address_and_contact(frm);
		}
		if (!frm.doc.date) {
			let currentDate = frappe.datetime.nowdate();
			frm.set_value("date", currentDate);
		}
		if (!frm.is_new()) {
			frm.add_custom_button(
				__("Sales Order"),
				function () {
					frappe.call({
						method: "utility_billing.utility_billing.doctype.utility_service_request.utility_service_request.create_customer_and_sales_order",
						args: {
							docname: frm.doc.name,
						},
						callback: function (response) {
							if (response.message) {
								let sales_order_link = frappe.utils.get_form_link(
									"Sales Order",
									response.message.sales_order
								);

								frappe.msgprint({
									title: __("Success"),
									message: __(
										"Sales Order <a href='{0}'>{1}</a> created successfully.",
										[sales_order_link, response.message.sales_order]
									),
									indicator: "green",
								});
							}
						},
					});
				},
				__("Create")
			).addClass("btn-primary");
			frm.page.set_inner_btn_group_as_primary(__("Create"));
		}
		if (frm.doc.customer) {
			fetch_customer_details(frm);
		}
	},

	customer: function (frm) {
		if (frm.doc.customer) {
			fetch_customer_details(frm);
		}
	},
});

frappe.ui.form.on("Utility Service Request Item", {
	items_add: function (frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		if (!row.delivery_date) {
			if (frm.doc.delivery_date) {
				frappe.model.set_value(cdt, cdn, "delivery_date", frm.doc.delivery_date);
			} else {
				frappe.model.set_value(cdt, cdn, "delivery_date", frappe.datetime.nowdate());
			}
		}
	},
	item_code: function (frm, cdt, cdn) {
		var row = locals[cdt][cdn];
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
						frappe.model.set_value(cdt, cdn, "rate", r.message.standard_rate);
						frappe.model.set_value(cdt, cdn, "warehouse", r.message.default_warehouse);
						frappe.model.set_value(cdt, cdn, "qty", 1);
						if (r.message.uoms[0]) {
							frappe.model.set_value(
								cdt,
								cdn,
								"conversion_factor",
								r.message.uoms[0].conversion_factor
							);
						}
						if (frm.doc.price_list) {
							frappe.call({
								method: "frappe.client.get",
								args: {
									doctype: "Item Price",
									filters: {
										price_list: frm.doc.price_list,
										item_code: row.item_code,
									},
								},
								callback: function (res) {
									if (res.message) {
										var amount = res.message.price_list_rate * row.qty;
										frappe.model.set_value(cdt, cdn, "amount", amount);
										frappe.model.set_value(
											cdt,
											cdn,
											"price_list_rate",
											res.message.price_list_rate
										);
										frappe.model.set_value(
											cdt,
											cdn,
											"base_price_list_rate",
											res.message.price_list_rate
										);
										frappe.model.set_value(
											cdt,
											cdn,
											"rate",
											res.message.price_list_rate
										);
									}
								},
							});
						}
					}
				},
			});
		}
	},
});

function fetch_customer_details(frm) {
	frappe.call({
		method: "utility_billing.utility_billing.doctype.meter_reading.meter_reading.get_customer_details",
		args: {
			customer: frm.doc.customer,
		},
		callback: function (r) {
			if (r.message) {
				frm.set_value("customer_name", r.message.customer_name);
				frm.set_value("territory", r.message.territory);
				frm.set_value("customer_group", r.message.customer_group);
				frm.set_value("customer_type", r.message.customer_type);
				frm.set_value("company", r.message.company);
				frm.set_value("tax_id", r.message.tax_id);
				frm.set_value("nrcpassport_no", r.message.nrc_or_passport_no);
			}
		},
	});
}
