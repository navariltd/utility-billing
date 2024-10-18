frappe.ui.form.on("Utility Service Request", {
	refresh: function (frm) {
		frm.toggle_display("address_html", !frm.is_new());
		frm.toggle_display("contact_html", !frm.is_new());
		frm.ignore_doctypes_on_cancel_all = ["BOM"];

		if (!frm.is_new()) {
			frappe.contacts.render_address_and_contact(frm);
			frappe.call({
				method: "utility_billing.utility_billing.doctype.utility_service_request.utility_service_request.check_request_status",
				args: {
					request_name: frm.doc.name,
				},
				callback: function (response) {
					if (response.message != frm.doc.request_status) {
						frm.set_value("request_status", response.message);
						frm.save();
					}

					addActionButtons(frm, frm.doc.request_status);
				},
			});
		}
		if (!frm.doc.date) {
			let currentDate = frappe.datetime.nowdate();
			frm.set_value("date", currentDate);
		}

		frm.fields_dict["items"].grid.get_field("item_code").get_query = function () {
			return {
				filters: {
					is_sales_item: 1,
					has_variants: 0,
				},
			};
		};

		frm.set_query("customer_group", function () {
			return {
				filters: {
					is_group: 0,
				},
			};
		});
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

	onload: function (frm) {
		frm.ignore_doctypes_on_cancel_all = ["BOM"];
	},
});

frappe.ui.form.on("Utility Service Request Item", {
	items_add: function (frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		let delivery_date = frm.doc.delivery_date || frappe.datetime.nowdate();
		frappe.model.set_value(cdt, cdn, "delivery_date", delivery_date);
		frm.script_manager.copy_from_first_row("items", row, [
			"income_account",
			"discount_account",
			"cost_center",
		]);
	},

	item_code: function (frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (row.item_code) {
			frappe.call({
				method: "utility_billing.utility_billing.doctype.utility_service_request.utility_service_request.get_item_details",
				args: {
					item_code: row.item_code,
					price_list: frm.doc.price_list,
				},
				callback: function (r) {
					if (r.message) {
						let item = r.message;
						frappe.model.set_value(cdt, cdn, {
							item_name: item.item_name,
							uom: item.uom,
							rate: item.rate,
							warehouse: item.warehouse,
							description: item.description,
							qty: 1,
							conversion_factor: item.conversion_factor,
							brand: item.brand,
							item_group: item.item_group,
							stock_uom: item.stock_uom,
							bom_no: item.bom_no,
							weight_per_unit: item.weight_per_unit,
							weight_uom: item.weight_uom,
						});

						let amount = flt(item.rate) * flt(row.qty || 1);
						frappe.model.set_value(cdt, cdn, {
							rate: item.rate,
							amount: amount,
							base_price_list_rate: item.rate,
						});
					}
				},
			});
		}
	},

	rate: function (frm, cdt, cdn) {
		calculate_amount(frm, cdt, cdn);
	},

	qty: function (frm, cdt, cdn) {
		calculate_amount(frm, cdt, cdn);
	},

	delivery_date: function (frm) {
		if (!frm.doc.delivery_date) {
			erpnext.utils.copy_value_in_all_rows(frm.doc, null, null, "items", "delivery_date");
		}
	},
});

function calculate_amount(frm, cdt, cdn) {
	let row = locals[cdt][cdn];
	let amount = flt(row.rate) * flt(row.qty);
	frappe.model.set_value(cdt, cdn, "amount", amount);
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
			},
		],
		primary_action_label: __("Create"),
		primary_action(values) {
			frappe.call({
				method: "utility_billing.utility_billing.doctype.utility_service_request.utility_service_request.create_bom",
				args: {
					docname: frm.doc.name,
					item_code: values.item_code,
				},
				callback: function (response) {
					if (response.message) {
						handle_response(response, "BOM", frm);
						modal.hide();

						frappe.set_route("Form", "BOM", response.message.bom);
					}
				},
			});
		},
	});

	modal.show();
}

function addActionButtons(frm) {
	const currentStatus = frm.doc.request_status;

	if (frm.doc.docstatus === 1) {
		frappe.db.get_value(
			"Sales Order",
			{ utility_service_request: frm.doc.name },
			"name",
			(r) => {
				if (!r.name) {
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
									if (response && response.message) {
										frappe.set_route(
											"Form",
											"Sales Order",
											response.message.sales_order
										);
									}
								},
							});
						},
						__("Create")
					);
				}
			}
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
						handle_response(response, __("Site Survey"), frm);
						if (response && response.message) {
							frappe.set_route("Form", "Issue", response.message.issue);
						}
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
