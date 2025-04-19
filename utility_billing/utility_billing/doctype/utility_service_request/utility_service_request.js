frappe.ui.form.on("Utility Service Request", {
	refresh: function (frm) {
		frm.toggle_display("address_html", !frm.is_new());
		frm.toggle_display("contact_html", !frm.is_new());
		frm.ignore_doctypes_on_cancel_all = ["BOM"];

		set_dynamic_field_label(frm);

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

	service_request_from(frm) {
		set_dynamic_field_label(frm);
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

function set_dynamic_field_label(frm) {
	if (frm.doc.service_request_from == "Customer") {
		frm.set_df_property("party_name", "label", "Customer");
		frm.fields_dict.party_name.get_query = null;
	} else if (frm.doc.service_request_from == "Lead") {
		frm.set_df_property("party_name", "label", "Lead");
		frm.fields_dict.party_name.get_query = function () {
			return { query: "erpnext.controllers.queries.lead_query" };
		};
	} else if (frm.doc.service_request_from == "Prospect") {
		frm.set_df_property("party_name", "label", "Prospect");
		frm.fields_dict.party_name.get_query = null;
	}
}

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
	frappe.db.get_value("Customer", frm.doc.customer, "customer_name").then((response) => {
		const customerName = response.message.customer_name;

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
					default: customerName,
					read_only: 1,
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
							warehouse:
								item.warehouse || frappe.defaults.get_user_default("Warehouse"),
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
						customer_name: values.customer_name,
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

		dialog.$wrapper.find(".modal-dialog").css("max-width", "max-content");
		dialog.$wrapper.find(".modal-content").css("width", "1000px");

		dialog.show();
	});
}

function showSalesInvoiceModal(frm) {
	frappe.db.get_value("Customer", frm.doc.customer, "customer_name").then((response) => {
		const customerName = response.message.customer_name;
		const today = frappe.datetime.get_today();
		const nextYear = frappe.datetime.add_days(today, 365);

		const dialog = new frappe.ui.Dialog({
			title: __("Create Sales Invoice"),
			fields: [
				// Customer Section
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
					default: customerName,
					read_only: 1,
				},
				{
					fieldname: "col_break",
					fieldtype: "Column Break",
				},
				{
					fieldname: "posting_date",
					label: __("Posting Date"),
					fieldtype: "Date",
					default: today,
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
					default: frappe.datetime.add_days(today, 30),
					reqd: 1,
				},

				// Auto Repeat Section
				{
					fieldname: "auto_repeat_section",
					fieldtype: "Section Break",
					label: __("Auto Repeat Settings"),
				},
				{
					fieldname: "enable_auto_repeat",
					label: __("Set Auto Repeat"),
					fieldtype: "Check",
					default: 0,
					change: function () {
						update_auto_repeat_fields(this.get_value(), dialog.get_value("frequency"));
					},
				},
				{
					fieldname: "frequency",
					label: __("Frequency"),
					fieldtype: "Select",
					default: "Monthly",
					options: "Weekly\nBi-Weekly\nMonthly\nQuarterly\nHalf-Yearly\nYearly",
					onchange: function () {
						if (dialog.get_value("enable_auto_repeat")) {
							update_auto_repeat_fields(true, this.get_value());
						}
					},
					depends_on: "eval:doc.enable_auto_repeat",
				},
				{
					fieldname: "col_break_auto",
					fieldtype: "Column Break",
				},
				{
					fieldname: "repeat_start_date",
					label: __("Start Date"),
					fieldtype: "Date",
					default: today,
					reqd: 1,
					depends_on: "eval:doc.enable_auto_repeat",
				},
				{
					fieldname: "repeat_end_date",
					label: __("End Date"),
					fieldtype: "Date",
					default: nextYear,
					reqd: 1,
					depends_on: "eval:doc.enable_auto_repeat",
				},
				{
					fieldname: "repeat_on_days",
					label: __("Repeat on Days"),
					fieldtype: "MultiSelect",
					options: [
						"Monday",
						"Tuesday",
						"Wednesday",
						"Thursday",
						"Friday",
						"Saturday",
						"Sunday",
					],
					depends_on:
						"eval:doc.enable_auto_repeat && (doc.frequency === 'Weekly' || doc.frequency === 'Bi-Weekly')",
				},

				// Items Section
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
							warehouse:
								item.warehouse || frappe.defaults.get_user_default("Warehouse"),
						};
					}),
				},
			],
			primary_action_label: __("Create"),
			primary_action: function (values) {
				const items = values.items_table.map((row) => ({
					name: row.name,
					item_code: row.item_code,
					qty: row.qty,
					rate: row.rate,
					amount: row.amount,
					warehouse: row.warehouse,
				}));

				const auto_repeat_settings = values.enable_auto_repeat
					? {
							frequency: values.frequency,
							start_date: values.repeat_start_date,
							end_date: values.repeat_end_date,
							days: values.repeat_on_days,
					  }
					: null;

				frappe.call({
					method: "utility_billing.utility_billing.doctype.utility_service_request.utility_service_request.create_sales_invoice_doc",
					args: {
						docname: frm.doc.name,
						items: items,
						customer: values.customer,
						customer_name: values.customer_name,
						posting_date: values.posting_date,
						due_date: values.due_date,
						company: values.company,
						auto_repeat: auto_repeat_settings,
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

		function update_auto_repeat_fields(enabled, frequency) {
			const isWeekly = ["Weekly", "Bi-Weekly"].includes(frequency);
			dialog.toggle_display("frequency", enabled);
			dialog.toggle_display("repeat_start_date", enabled);
			dialog.toggle_display("repeat_end_date", enabled);
			dialog.toggle_display("repeat_on_days", enabled && isWeekly);
		}

		dialog.$wrapper.find(".modal-dialog").css("max-width", "max-content");
		dialog.$wrapper.find(".modal-content").css("width", "1000px");
		dialog.show();
	});
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
