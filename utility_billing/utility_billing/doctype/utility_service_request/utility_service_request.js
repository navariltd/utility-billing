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
					is_utility_item: 1,
					has_variants: 0,
				},
			};
		};

		let closedWarrantySerials = [];

		frappe.db
			.get_list("Warranty Claim", {
				filters: { status: "Closed" },
				fields: ["serial_no"],
			})
			.then((warrantyClaims) => {
				closedWarrantySerials = warrantyClaims.map((claim) => claim.serial_no);
			});

		frm.fields_dict["items"].grid.get_field("meter_number").get_query = function () {
			return {
				filters: {
					status: "Active",
					name: ["not in", closedWarrantySerials],
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

	property: function (frm) {
		if (frm.doc.property) {
			frappe.call({
				method: "frappe.client.get_value",
				args: {
					doctype: "Utility Property",
					fieldname: "territory",
					filters: {
						name: frm.doc.property,
					},
				},
				callback: function (r) {
					if (r.message && r.message.territory) {
						frm.set_value("territory", r.message.territory);
					}
				},
			});
		}
	},

	tc_name: function (frm) {
		if (!frm.doc.tc_name) {
			frm.set_value("terms", "");
			return;
		}
		frappe.call({
			method: "frappe.client.get_value",
			args: {
				doctype: "Terms and Conditions",
				fieldname: "terms",
				filters: {
					name: frm.doc.tc_name,
				},
			},
			callback: function (r) {
				if (r.message && r.message.terms) {
					frm.set_value("terms", r.message.terms);
				}
			},
		});
	},

	onload: function (frm) {
		frm.ignore_doctypes_on_cancel_all = ["BOM"];
	},
});

frappe.ui.form.on("Utility Service Request Item", {
	form_render: function (frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		handle_item_code(frm, cdt, cdn, row.item_code);
	},

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
		handle_item_code(frm, cdt, cdn, row.item_code, true);
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

function handle_item_code(frm, cdt, cdn, item_code, update_fields = false) {
	if (item_code) {
		frappe.call({
			method: "utility_billing.utility_billing.doctype.utility_service_request.utility_service_request.get_item_details",
			args: {
				item_code: item_code,
				price_list: frm.doc.price_list,
			},
			callback: function (r) {
				if (r.message) {
					let item = r.message;
					if (update_fields) {
						update_item_fields(frm, cdt, cdn, item);
					}
					toggle_meter_number(frm, cdt, cdn, item.item_group === "Meter");
				}
			},
		});
	} else {
		toggle_meter_number(frm, cdt, cdn, false);
	}
}

function update_item_fields(frm, cdt, cdn, item) {
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
		item_tax_template: item.item_tax_template,
		warehouse: item.default_warehouse,
	});

	let amount = flt(item.rate) * flt(frm.doc.qty || 1);
	frappe.model.set_value(cdt, cdn, {
		rate: item.rate,
		amount: amount,
		base_price_list_rate: item.rate,
	});
}

function toggle_meter_number(frm, cdt, cdn, show) {
	frm.fields_dict["items"].grid.toggle_display("meter_number", show, cdt, cdn);
	if (!show) {
		frappe.model.set_value(cdt, cdn, "meter_number", null);
	}
	frm.fields_dict["items"].grid.toggle_reqd("warehouse", show, cdt, cdn);
}

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
						const bomUrl = frappe.utils.get_form_link("BOM", response.message.bom);
						window.location.href = bomUrl;
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
		if (!frm.doc.customer) {
			frm.add_custom_button(
				__("Customer"),
				function () {
					frappe.call({
						method: "utility_billing.utility_billing.doctype.utility_service_request.utility_service_request.make_customer",
						args: {
							name: frm.doc.name,
						},
						callback: function (response) {
							frappe.show_alert({
								message: __("Customer created successfully!"),
								indicator: "green",
							});
							frm.reload_doc();
						},
					});
				},
				__("Create")
			);
		} else {
			frappe.db.get_value(
				"Contract",
				{ utility_service_request: frm.doc.name },
				"name",
				(r) => {
					if (!r.name) {
						frm.add_custom_button(
							__("Contract"),
							function () {
								frappe.call({
									method: "utility_billing.utility_billing.doctype.utility_service_request.utility_service_request.create_contract",
									args: {
										name: frm.doc.name,
									},
									callback: function (response) {
										handle_response(response, __("Contract"), frm);
										if (response && response.message) {
											frappe.set_route("Form", "Contract", response.message);
										}
									},
								});
							},
							__("Create")
						);
					}
				}
			);

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
												response.message.name
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
	}

	if (currentStatus === "") {
		frm.add_custom_button(
			__("Site Survey"),
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
				const dialog = new frappe.ui.Dialog({
					title: __("Select or Create BOM"),
					fields: [
						{
							fieldname: "selected_bom",
							label: __("Select BOM"),
							fieldtype: "Link",
							options: "BOM",
						},
					],
					primary_action_label: __("New BOM"),
					primary_action: function () {
						const new_bom = frappe.model.get_new_doc("BOM");
						new_bom.utility_service_request = frm.doc.name;

						frappe.set_route("Form", "BOM", new_bom.name);
					},
					secondary_action_label: __("New Version"),
					secondary_action: function () {
						const selected_bom = dialog.get_value("selected_bom");
						if (selected_bom) {
							frappe.call({
								method: "utility_billing.utility_billing.doctype.utility_service_request.utility_service_request.bom_new_version",
								args: {
									bom: selected_bom,
								},
								callback: function (response) {
									if (response && response.message) {
										const new_bom = response.message;
										new_bom.utility_service_request = frm.doc.name;
										frappe.db
											.insert(new_bom)
											.then((doc) => {
												frappe.set_route("Form", "BOM", doc.name);
											})
											.catch((err) => {
												frappe.msgprint({
													title: __("Error"),
													message:
														__("Failed to save the BOM: ") +
														err.message,
													indicator: "red",
												});
											});
									}
								},
							});
						} else {
							frappe.msgprint(__("Please select a BOM to create a new version."));
						}
					},
				});

				dialog.show();
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
