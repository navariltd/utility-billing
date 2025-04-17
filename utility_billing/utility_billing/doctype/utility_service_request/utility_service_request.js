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

	utility_bill_structure(frm) {
		if (!frm.doc.utility_bill_structure) return;

		frappe.call({
			method: "utility_billing.utility_billing.doctype.utility_service_request.utility_service_request.get_utility_bill_structure_details",
			args: { name: frm.doc.utility_bill_structure },
			callback(r) {
				if (!r.message) return;

				const { items, dimensions } = r.message;

				frm.clear_table("items");
				(items || []).forEach((item) => {
					const row = frm.add_child("items");
					Object.keys(item).forEach((field) => {
						row[field] = item[field];
					});
				});
				frm.refresh_field("items");

				Object.entries(dimensions || {}).forEach(([key, value]) => {
					if (frm.fields_dict[key]) {
						frm.set_value(key, value);
					}
				});
			},
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
		// Customer creation button
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
			// Contract creation button
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

			// Sales Order button with modal
			if (frm.doc.items && frm.doc.items.length > 0) {
				frappe.db.get_value(
					"Sales Order",
					{ utility_service_request: frm.doc.name },
					"name",
					(r) => {
						if (!r.name) {
							frm.add_custom_button(
								__("Sales Order"),
								function () {
									showSalesOrderModal(frm);
								},
								__("Create")
							);
						}
					}
				);
			}

			// Sales Invoice button with modal
			if (frm.doc.items && frm.doc.items.length > 0) {
				frappe.db.get_value(
					"Sales Invoice",
					{ utility_service_request: frm.doc.name },
					"name",
					(r) => {
						if (!r.name) {
							frm.add_custom_button(
								__("Sales Invoice"),
								function () {
									showSalesInvoiceModal(frm);
								},
								__("Create")
							);
						}
					}
				);
			}
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

function showSalesOrderModal(frm) {
	const dialog = new frappe.ui.Dialog({
		title: __("Create Sales Order"),
		fields: [
			{
				fieldname: "customer_section",
				fieldtype: "Section Break",
				label: __("Customer Details"),
				collapsible: 0,
			},
			{
				fieldname: "customer",
				label: __("Customer"),
				fieldtype: "Link",
				options: "Customer",
				default: frm.doc.customer,
				read_only: 1,
			},
			{
				fieldname: "customer_name",
				label: __("Customer Name"),
				fieldtype: "Data",
				default: frm.doc.customer_name,
				read_only: 1,
				collapsible: 0,
			},
			{
				fieldname: "col_break",
				fieldtype: "Column Break",
			},
			{
				fieldname: "transaction_date",
				label: __("Date"),
				fieldtype: "Date",
				default: frappe.datetime.get_today(),
				reqd: 1,
			},
			{
				fieldname: "company",
				label: __("Company"),
				fieldtype: "Link",
				options: "Company",
				default: frappe.defaults.get_user_default("Company"),
				reqd: 1,
			},
			{
				fieldname: "items_section",
				fieldtype: "Section Break",
				label: __("Select Items"),
				collapsible: 0,
			},
			{
				fieldname: "items_table",
				fieldtype: "Table",
				label: __("Items"),
				fields: [
					{
						fieldname: "item_code",
						label: __("Item"),
						fieldtype: "Link",
						options: "Item",
						in_list_view: 1,
						reqd: 1,
						onchange: function () {
							const row = this.grid_row;
							if (this.value) {
								frappe.call({
									method: "frappe.client.get_value",
									args: {
										doctype: "Item",
										fieldname: ["item_name", "standard_rate"],
										filters: { name: this.value },
									},
									callback: (r) => {
										if (!r.exc) {
											row.doc.item_name = r.message.item_name;
											row.doc.rate = r.message.standard_rate;
											calculate_row_amount(row);
											refresh_field("items_table");
										}
									},
								});
							}
						},
					},
					{
						fieldname: "qty",
						fieldtype: "Float",
						label: __("Qty"),
						in_list_view: 1,
						default: 1,
						reqd: 1,
						onchange: function () {
							calculate_row_amount(this.grid_row);
						},
					},
					{
						fieldname: "rate",
						label: __("Rate"),
						fieldtype: "Currency",
						in_list_view: 1,
						reqd: 1,
						onchange: function () {
							calculate_row_amount(this.grid_row);
						},
					},
					{
						fieldname: "amount",
						label: __("Amount"),
						fieldtype: "Currency",
						read_only: 1,
						in_list_view: 1,
					},
					{
						fieldname: "warehouse",
						label: __("Warehouse"),
						fieldtype: "Link",
						options: "Warehouse",
						reqd: 1,
						default: frappe.defaults.get_user_default("Warehouse"),
						in_list_view: 1,
					},
					{
						fieldname: "name",
						fieldtype: "Data",
						hidden: 1,
					},
				],
				data: frm.doc.items.map((item) => {
					const qty = item.qty || 1;
					const rate = item.rate || 0;
					return {
						name: item.name,
						item_code: item.item_code,
						rate: rate,
						amount: flt(rate * qty),
						qty: qty,
						warehouse: item.warehouse || frappe.defaults.get_user_default("Warehouse"),
					};
				}),
			},
		],
		primary_action_label: __("Create"),
		primary_action: function (values) {
			const items = values.items_table.map((row) => {
				return {
					name: row.name,
					item_code: row.item_code,
					qty: row.qty,
					rate: row.rate,
					amount: row.amount,
					warehouse: row.warehouse,
				};
			});

			frappe.call({
				method: "utility_billing.utility_billing.doctype.utility_service_request.utility_service_request.create_sales_order_doc",
				args: {
					docname: frm.doc.name,
					items: items,
					customer: values.customer,
					transaction_date: values.transaction_date,
					company: values.company,
				},
				callback: function (response) {
					dialog.hide();
					if (response.message) {
						frappe.show_alert({
							message: __("Sales Order created successfully!"),
							indicator: "green",
						});
						frappe.set_route("Form", "Sales Order", response.message);
					}
				},
			});
		},
	});

	function calculate_row_amount(row) {
		const qty = parseFloat(row.doc.qty) || 0;
		const rate = parseFloat(row.doc.rate) || 0;
		row.doc.amount = parseFloat(qty * rate);
		row.grid.refresh();
	}

	dialog.show();
}

function showSalesInvoiceModal(frm) {
	const dialog = new frappe.ui.Dialog({
		title: __("Create Sales Invoice"),
		fields: [
			{
				fieldname: "customer_section",
				fieldtype: "Section Break",
				label: __("Customer Details"),
				collapsible: 0,
			},
			{
				fieldname: "customer",
				label: __("Customer"),
				fieldtype: "Link",
				options: "Customer",
				default: frm.doc.customer,
				read_only: 1,
			},
			{
				fieldname: "customer_name",
				label: __("Customer Name"),
				fieldtype: "Data",
				default: frm.doc.customer_name,
				read_only: 1,
				collapsible: 0,
			},
			{
				fieldname: "col_break",
				fieldtype: "Column Break",
			},
			{
				fieldname: "posting_date",
				label: __("Posting Date"),
				fieldtype: "Date",
				default: frappe.datetime.get_today(),
				reqd: 1,
			},
			{
				fieldname: "company",
				label: __("Company"),
				fieldtype: "Link",
				options: "Company",
				default: frappe.defaults.get_user_default("Company"),
				reqd: 1,
			},
			{
				fieldname: "due_date",
				label: __("Due Date"),
				fieldtype: "Date",
				default: frappe.datetime.add_days(frappe.datetime.get_today(), 30),
				reqd: 1,
			},
			{
				fieldname: "items_section",
				fieldtype: "Section Break",
				label: __("Select Items"),
				collapsible: 0,
			},
			{
				fieldname: "items_table",
				fieldtype: "Table",
				label: __("Items"),
				fields: [
					{
						fieldname: "item_code",
						label: __("Item"),
						fieldtype: "Link",
						options: "Item",
						in_list_view: 1,
						reqd: 1,
						onchange: function () {
							const row = this.grid_row;
							if (this.value) {
								frappe.call({
									method: "frappe.client.get_value",
									args: {
										doctype: "Item",
										fieldname: ["item_name", "standard_rate"],
										filters: { name: this.value },
									},
									callback: (r) => {
										if (!r.exc) {
											row.doc.item_name = r.message.item_name;
											row.doc.rate = r.message.standard_rate;
											calculate_row_amount(row);
											refresh_field("items_table");
										}
									},
								});
							}
						},
					},
					{
						fieldname: "qty",
						label: __("Quantity"),
						fieldtype: "Float",
						default: 1,
						in_list_view: 1,
						reqd: 1,
						onchange: function () {
							calculate_row_amount(this.grid_row);
						},
					},
					{
						fieldname: "rate",
						label: __("Rate"),
						fieldtype: "Currency",
						in_list_view: 1,
						reqd: 1,
						onchange: function () {
							calculate_row_amount(this.grid_row);
						},
					},
					{
						fieldname: "amount",
						label: __("Amount"),
						fieldtype: "Currency",
						read_only: 1,
						in_list_view: 1,
					},
					{
						fieldname: "warehouse",
						label: __("Warehouse"),
						fieldtype: "Link",
						options: "Warehouse",
						reqd: 1,
						default: frappe.defaults.get_user_default("Warehouse"),
						in_list_view: 1,
					},
					{
						fieldname: "name",
						fieldtype: "Data",
						hidden: 1,
					},
				],
				data: frm.doc.items.map((item) => {
					const qty = item.qty || 1;
					const rate = item.rate || 0;
					return {
						name: item.name,
						item_code: item.item_code,
						qty: qty,
						rate: rate,
						amount: flt(rate * qty),
						warehouse: item.warehouse || frappe.defaults.get_user_default("Warehouse"),
					};
				}),
			},
		],
		primary_action_label: __("Create"),
		primary_action: function (values) {
			const items = values.items_table.map((row) => {
				return {
					name: row.name,
					item_code: row.item_code,
					qty: row.qty,
					rate: row.rate,
					amount: row.amount,
					warehouse: row.warehouse,
				};
			});

			frappe.call({
				method: "utility_billing.utility_billing.doctype.utility_service_request.utility_service_request.create_sales_invoice_doc",
				args: {
					docname: frm.doc.name,
					items: items,
					customer: values.customer,
					posting_date: values.posting_date,
					due_date: values.due_date,
					company: values.company,
				},
				callback: function (response) {
					dialog.hide();
					if (response.message) {
						frappe.show_alert({
							message: __("Sales Invoice created successfully!"),
							indicator: "green",
						});
						frappe.set_route("Form", "Sales Invoice", response.message);
					}
				},
			});
		},
	});

	function calculate_row_amount(row) {
		const qty = parseFloat(row.doc.qty) || 0;
		const rate = parseFloat(row.doc.rate) || 0;
		row.doc.amount = parseFloat(qty * rate);
		row.grid.refresh();
	}

	dialog.show();
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
