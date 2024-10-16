frappe.ui.form.on("Utility Service Request", {
	refresh: function (frm) {
		frm.toggle_display("address_html", !frm.is_new());
		frm.toggle_display("contact_html", !frm.is_new());

		if (!frm.is_new()) {
			frappe.contacts.render_address_and_contact(frm);
			frappe.call({
				method: "utility_billing.utility_billing.doctype.utility_service_request.utility_service_request.check_request_status",
				args: {
					request_name: frm.doc.name,
				},
				callback: function (response) {
					if (response.message != frm.doc.status) {
						frm.set_value("status", response.message);
						frm.save();
					}

					addActionButtons(frm, frm.doc.status);
				},
			});
		}
		if (!frm.doc.date) {
			let currentDate = frappe.datetime.nowdate();
			frm.set_value("date", currentDate);
		}

		if (frm.doc.customer) {
			fetch_customer_details(frm);
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
			fetch_customer_details(frm);
		}
	},

	customer_group: function (frm) {
		if (frm.doc.customer_group) {
			frappe.call({
				method: "frappe.client.get_value",
				args: {
					doctype: "Customer Group",
					fieldname: "default_price_list",
					filters: {
						name: frm.doc.customer_group,
					},
				},
				callback: function (r) {
					if (r.message && r.message.default_price_list) {
						frm.set_value("price_list", r.message.default_price_list);
					}
				},
			});
		}
	},
});

frappe.ui.form.on("Utility Service Request Item", {
	items_add: function (frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		let delivery_date = frm.doc.delivery_date || frappe.datetime.nowdate();
		frappe.model.set_value(cdt, cdn, "delivery_date", delivery_date);
	},

	item_code: function (frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (row.item_code) {
			frappe.call({
				method: "frappe.client.get",
				args: { doctype: "Item", name: row.item_code },
				callback: function (r) {
					if (r.message) {
						let item = r.message;
						frappe.model.set_value(cdt, cdn, {
							item_name: item.item_name,
							uom: item.stock_uom,
							rate: item.standard_rate,
							warehouse: item.default_warehouse,
							description: item.description,
							qty: 1,
							conversion_factor: (item.uoms[0] || {}).conversion_factor || 1,
							brand: item.brand || null,
							item_group: item.item_group,
							stock_uom: item.stock_uom,
							bom_no: item.default_bom,
							weight_per_unit: item.weight_per_unit,
							weight_uom: item.weight_uom || null,
						});

						// Fetch price list rate if available
						if (frm.doc.price_list) {
							frappe.call({
								method: "frappe.client.get_list",
								args: {
									doctype: "Item Price",
									filters: {
										price_list: frm.doc.price_list,
										item_code: row.item_code,
									},
									fields: ["price_list_rate"],
								},
								callback: function (res) {
									let rate =
										res.message[0]?.price_list_rate || item.standard_rate;
									let amount = rate * row.qty;
									frappe.model.set_value(cdt, cdn, {
										rate: rate,
										price_list_rate: rate,
										amount: amount,
										base_price_list_rate: rate,
									});
								},
							});
						}
					}
				},
			});
		}
	},

	delivery_date: function (frm) {
		if (!frm.doc.delivery_date) {
			erpnext.utils.copy_value_in_all_rows(frm.doc, null, null, "items", "delivery_date");
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
function open_bom_creation_modal(frm) {
	const modal = new frappe.ui.Dialog({
		title: __("Create BOM"),
		fields: [
			{
				fieldname: "item_code",
				fieldtype: "Link",
				options: "Item",
				label: __("Select Item"),
				reqd: 1,
				get_query: function () {
					let item_codes = frm.doc.items.map((item) => item.item_code);
					return {
						query: "erpnext.controllers.queries.item_query",
						filters: {
							// has_bom: 1,
							item_code: ["in", item_codes],
						},
					};
				},

				change: function () {},
			},
			{
				fieldname: "items",
				fieldtype: "Table",
				label: __("Raw Materials"),
				fields: [
					{
						fieldname: "item_code",
						fieldtype: "Link",
						options: "Item",
						label: __("Item Code"),
						in_list_view: 1,
						read_only: 0,
						get_query: function () {
							return {
								filters: {
									include_item_in_manufacturing: 1,
									is_fixed_asset: 0,
								},
							};
						},
					},

					{
						fieldname: "qty",
						fieldtype: "Int",
						label: __("Quantity"),
						in_list_view: 1,
						reqd: 1,
					},
					{
						fieldname: "uom",
						fieldtype: "Link",
						options: "UOM",
						label: __("UOM"),
						in_list_view: 1,
						read_only: 0,
					},
					{
						fieldname: "conversion_factor",
						fieldtype: "Float",
						label: __("Conversion Factor"),
						in_list_view: 1,
						read_only: 0,
					},
				],
				reqd: 1,
			},
		],
		primary_action_label: __("Create"),
		primary_action(values) {
			// Call the method to create the BOM
			frappe.call({
				method: "utility_billing.utility_billing.doctype.utility_service_request.utility_service_request.create_bom",
				args: {
					docname: frm.doc.name,
					item_code: values.item_code,
					items: values.items,
				},
				callback: function (response) {
					handle_response(response, "BOM", frm);
					modal.hide();
				},
			});
		},
	});

	modal.show();
}
function addActionButtons(frm) {
	const currentStatus = frm.doc.status;

	if (frm.doc.docstatus === 1 && !frm.doc.sales_order) {
		frm.add_custom_button(
			__("Sales Order"),
			function () {
				frappe.call({
					method: "utility_billing.utility_billing.doctype.utility_service_request.utility_service_request.create_customer_and_sales_order",
					args: {
						docname: frm.doc.name,
					},
					callback: function (response) {
						handle_response(response, __("Sales Order"), frm);
					},
				});
			},
			__("Create")
		);
	}

	if (currentStatus === "") {
		frm.add_custom_button(
			__("Issue Site Survey"),
			function () {
				frappe.call({
					method: "utility_billing.utility_billing.doctype.utility_service_request.utility_service_request.create_site_survey",
					args: {
						docname: frm.doc.name,
					},
					callback: function (response) {
						handle_response(response, __("Issue Site Survey"), frm);
					},
				});
			},
			__("Create")
		);
	} else if (currentStatus === "Site Survey Completed") {
		frm.add_custom_button(
			__("BOM"),
			function () {
				open_bom_creation_modal(frm);
			},
			__("Create")
		);
	}
}

// Handle the response from the server
function handle_response(response, actionLabel, frm) {
	if (response.message) {
		frappe.show_alert({ message: `${actionLabel} created successfully!`, indicator: "green" });
		frm.reload_doc();
	} else {
		frappe.show_alert({ message: `Error while creating ${actionLabel}!`, indicator: "red" });
	}
}
