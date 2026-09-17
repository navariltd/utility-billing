const settingsDoctypeName = "Utility Billing Settings";

frappe.ui.form.on("Utility Service Request", {
	refresh: async function (frm) {
		frm.toggle_display("address_html", !frm.is_new());
		frm.toggle_display("contact_html", !frm.is_new());
		frm.ignore_doctypes_on_cancel_all = ["BOM"];

		set_dynamic_field_label(frm);

		if (!frm.is_new()) {
			frappe.contacts.render_address_and_contact(frm);
			load_item_price_summary(frm);
			frappe.call({
				method: "utility_billing.utility_billing.doctype.utility_service_request.utility_service_request.update_request_status",
				args: {
					request_name: frm.doc.name,
				},
				callback: function (response) {
					// if (response.message != frm.doc.request_status) {
					// 	frm.set_value("request_status", response.message);
					// 	frm.save();
					// }

					addActionButtons(frm, response.message);
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

		frm.fields_dict["utility_bill_structure"].get_query = function () {
			return {
				filters: {
					company: frm.doc.company || frappe.defaults.get_user_default("Company"),
				},
			};
		};

		frm.fields_dict["requested_properties"].grid.get_field("utility_property").get_query =
			function (doc, cdt, cdn) {
				const row = locals[cdt][cdn];

				const selectedProperties = [];
				(doc.requested_properties || []).forEach(function (d) {
					if (d.name !== row.name && d.utility_property) {
						selectedProperties.push(d.utility_property);
					}
				});

				let filters = {
					status: "Available",
					is_group: 0,
					company: frm.doc.company || frappe.defaults.get_user_default("Company"),
				};

				if (frm.doc.utility_property) {
					filters.parent_utility_property = frm.doc.utility_property;
				}

				if (selectedProperties.length > 0) {
					filters.name = ["not in", selectedProperties];
				}

				return {
					filters: filters,
				};
			};

		frm.get_selected_utility_properties = function () {
			let selected = [];

			(frm.doc.requested_properties || []).forEach((row) => {
				if (row.utility_property) {
					selected.push(row.utility_property);
				}
			});

			if (frm.doc.utility_property) {
				selected.push(frm.doc.utility_property);
			}

			return [...new Set(selected)];
		};

		frm.fields_dict["items"].grid.get_field("utility_property").get_query = function () {
			const selected_properties = frm.get_selected_utility_properties();

			return {
				filters: {
					name: ["in", selected_properties.length ? selected_properties : ["__none"]],
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

	customer: function (frm) {
		default_price_list_from_customer(frm);
	},

	party_name: function (frm) {
		if (frm.doc.service_request_from === "Customer") {
			default_price_list_from_customer(frm);
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

	start_date: function (frm) {
		update_contract_fields(frm, "start_date");
	},

	end_date: function (frm) {
		update_contract_fields(frm, "end_date");
	},

	contract_length_months: function (frm) {
		update_contract_fields(frm, "contract_length_months");
	},

	contract_template: function (frm) {
		if (frm.doc.contract_template) {
			frappe.call({
				method: "erpnext.crm.doctype.contract_template.contract_template.get_contract_template",
				args: {
					template_name: frm.doc.contract_template,
					doc: frm.doc,
				},
				callback: function (r) {
					if (r && r.message) {
						let contract_template = r.message.contract_template;
						frm.set_value("contract_terms", r.message.contract_terms);
						frm.set_value(
							"requires_fulfilment",
							contract_template.requires_fulfilment,
						);

						if (frm.doc.requires_fulfilment) {
							r.message.contract_template.fulfilment_terms.forEach((element) => {
								let d = frm.add_child("fulfilment_terms");
								d.requirement = element.requirement;
							});
							frm.refresh_field("fulfilment_terms");
						}
					}
				},
			});
		}
	},

	onload: function (frm) {
		frm.ignore_doctypes_on_cancel_all = ["BOM"];
	},

	price_list: function (frm) {
		refresh_property_item_rates(frm);
	},
});

/**
 * Re-resolve the property item rates when the price list changes.
 *
 * Without a price list the items keep their standard rate, so this only runs
 * once a price list is set.
 */
function refresh_property_item_rates(frm) {
	if (!frm.doc.price_list) return;

	const properties = (frm.doc.requested_properties || [])
		.map((row) => row.utility_property)
		.filter(Boolean);

	if (!properties.length) return;

	frappe.call({
		method: "utility_billing.utility_billing.doctype.utility_service_request.utility_service_request.get_service_items_for_properties",
		args: { properties, price_list: frm.doc.price_list },
		callback: function (response) {
			if (!response.message) return;

			let changed = false;
			response.message.forEach((details) => {
				const row = (frm.doc.items || []).find(
					(item) => item.utility_property === details.utility_property
				);
				if (!row || !details.rate || flt(row.rate) === flt(details.rate)) return;

				frappe.model.set_value(row.doctype, row.name, "rate", details.rate);
				frappe.model.set_value(
					row.doctype,
					row.name,
					"amount",
					flt(details.rate) * flt(row.qty || 1)
				);
				changed = true;
			});

			if (changed) frm.refresh_field("items");
		},
	});
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
});

frappe.ui.form.on("Contract Utility Property Item", {
	requested_properties_add: function (frm, cdt, cdn) {
		if (frm.doc.start_date) {
			frappe.model.set_value(cdt, cdn, "start_date", frm.doc.start_date);
		}
		if (frm.doc.end_date) {
			frappe.model.set_value(cdt, cdn, "end_date", frm.doc.end_date);
		}
		if (frm.doc.contract_length_months) {
			frappe.model.set_value(
				cdt,
				cdn,
				"contract_length_months",
				frm.doc.contract_length_months,
			);
		}
	},
	utility_property: function (frm) {
		sync_items_from_properties(frm);
	},
	requested_properties_remove: function (frm) {
		sync_items_from_properties(frm);
	},
	start_date: (frm, cdt, cdn) => update_child_contract_fields(frm, cdt, cdn, "start_date"),
	end_date: (frm, cdt, cdn) => update_child_contract_fields(frm, cdt, cdn, "end_date"),
	contract_length_months: (frm, cdt, cdn) =>
		update_child_contract_fields(frm, cdt, cdn, "contract_length_months"),
});

/**
 * Default the price list from the customer when the document has none.
 *
 * An explicitly chosen price list is never overwritten, so a user edit sticks.
 */
function default_price_list_from_customer(frm) {
	if (frm.doc.price_list) return;

	const customer = frm.doc.customer || frm.doc.party_name;
	if (!customer || !frappe.db.exists("Customer", customer)) return;

	frappe.db.get_value("Customer", customer, "default_price_list").then((response) => {
		const price_list = response?.message?.default_price_list;
		if (price_list) frm.set_value("price_list", price_list);
	});
}

/**
 * Ensure every requested property has its service item in the items table.
 *
 * The item rows are keyed by property, so removing a property drops its row
 * and re-adding it does not duplicate. Rows are only ever added for
 * properties, so hand-added items are left untouched.
 */
function sync_items_from_properties(frm) {
	const properties = (frm.doc.requested_properties || [])
		.map((row) => row.utility_property)
		.filter(Boolean);

	drop_orphan_property_items(frm, properties);

	if (!properties.length) return;

	frappe.call({
		method: "utility_billing.utility_billing.doctype.utility_service_request.utility_service_request.get_service_items_for_properties",
		args: { properties, price_list: frm.doc.price_list },
		callback: function (response) {
			if (!response.message) return;

			let added = false;
			response.message.forEach((details) => {
				if (add_property_item_row(frm, details)) added = true;
			});

			if (added) frm.refresh_field("items");
		},
	});
}

/**
 * Append an item row for a property unless it is already present.
 *
 * Returns whether a row was added.
 */
function add_property_item_row(frm, details) {
	const exists = (frm.doc.items || []).some(
		(row) => row.utility_property === details.utility_property
	);
	if (exists) return false;

	const row = frm.add_child("items");
	const allowed = Object.keys(frm.fields_dict.items.grid.docfields).length
		? frm.fields_dict.items.grid.docfields.map((field) => field.fieldname)
		: null;

	Object.entries(details).forEach(([field, value]) => {
		// Only set fields the child table actually has.
		if (allowed && !allowed.includes(field)) return;
		row[field] = value;
	});

	if (!row.qty) row.qty = 1;
	if (!row.delivery_date) row.delivery_date = frm.doc.delivery_date || frappe.datetime.nowdate();

	return true;
}

/**
 * Remove item rows whose property is no longer requested.
 */
function drop_orphan_property_items(frm, properties) {
	const orphans = (frm.doc.items || []).filter(
		(row) => row.utility_property && !properties.includes(row.utility_property)
	);

	if (!orphans.length) return;

	orphans.forEach((row) => frappe.model.clear_doc(row.doctype, row.name));
	frm.refresh_field("items");
}

function set_dynamic_field_label(frm) {
	if (frm.doc.service_request_from == "Customer") {
		frm.set_df_property("party_name", "label", "Customer");
		frm.set_df_property("customer", "hidden", 1);
	} else if (frm.doc.service_request_from == "Lead") {
		frm.set_df_property("party_name", "label", "Lead");
	} else if (frm.doc.service_request_from == "Prospect") {
		frm.set_df_property("party_name", "label", "Prospect");
	} else if (frm.doc.service_request_from == "CRM Deal") {
		frm.set_df_property("party_name", "label", "Frappe CRM Deal");
	}

	frm.fields_dict.party_name.get_query = null;
}

function update_child_contract_fields(frm, cdt, cdn, changed_field) {
	const row = locals[cdt][cdn];

	const parent_start = frm.doc.start_date
		? frappe.datetime.str_to_obj(frm.doc.start_date)
		: null;
	const parent_end = frm.doc.end_date ? frappe.datetime.str_to_obj(frm.doc.end_date) : null;

	const start = row.start_date ? frappe.datetime.str_to_obj(row.start_date) : null;
	const end = row.end_date ? frappe.datetime.str_to_obj(row.end_date) : null;
	const length = row.contract_length_months;

	if (start && parent_start && start < parent_start) {
		frappe.model.set_value(cdt, cdn, "start_date", null);
		frappe.msgprint("Property start date cannot be before contract start date.");
		return;
	}

	if (end && parent_end && end > parent_end) {
		frappe.model.set_value(cdt, cdn, "end_date", null);
		frappe.msgprint("Property end date cannot be after contract end date.");
		return;
	}

	if (changed_field === "start_date" && end) {
		const diff = get_month_diff(end, start);
		frappe.model.set_value(cdt, cdn, "contract_length_months", diff);
	} else if (changed_field === "end_date" && start) {
		const diff = get_month_diff(end, start);
		frappe.model.set_value(cdt, cdn, "contract_length_months", diff);
	} else if (changed_field === "contract_length_months" && start && length != null) {
		let new_end = frappe.datetime.add_months(start, length);
		const parent_end_date = parent_end ? frappe.datetime.str_to_obj(parent_end) : null;
		const new_end_date = new_end ? new_end : null;

		if (parent_end_date && new_end_date && new_end_date > parent_end_date) {
			new_end = parent_end_date;
			frappe.msgprint("Adjusted property end date to match contract end date.");
		}

		frappe.model.set_value(cdt, cdn, "end_date", frappe.datetime.obj_to_str(new_end));
	}

	if (row.start_date && row.end_date) {
		const diff = get_month_diff(row.start_date, row.end_date);
		frappe.model.set_value(cdt, cdn, "contract_length_months", diff);
	}
}

function get_month_diff(start_date, end_date) {
	const start = frappe.datetime.str_to_obj(start_date);
	const end = frappe.datetime.str_to_obj(end_date);

	let months;
	months = (end.getFullYear() - start.getFullYear()) * 12;
	months -= start.getMonth();
	months += end.getMonth();

	if (end.getDate() < start.getDate()) {
		months -= 1;
	}

	return months <= 0 ? 0 : months;
}

function update_contract_fields(frm, changed_field) {
	const start = frm.doc.start_date ? frappe.datetime.str_to_obj(frm.doc.start_date) : null;
	const end = frm.doc.end_date ? frappe.datetime.str_to_obj(frm.doc.end_date) : null;
	const length = frm.doc.contract_length_months;

	if (changed_field === "start_date" && end) {
		const months = get_month_diff(start, end);
		frm.set_value("contract_length_months", months);
	} else if (changed_field === "end_date" && start) {
		const months = get_month_diff(start, end);
		frm.set_value("contract_length_months", months);
	} else if (changed_field === "contract_length_months" && start && length !== undefined) {
		const new_end = frappe.datetime.add_months(start, length);
		frm.set_value("end_date", frappe.datetime.obj_to_str(new_end));
	}
}

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

function get_customer_section_fields(frm, customerName) {
	return [
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
			fieldname: "col_break_customer",
			fieldtype: "Column Break",
		},
		{
			fieldname: "customer_name",
			label: __("Customer Name"),
			fieldtype: "Data",
			default: customerName,
			read_only: 1,
		},
	];
}

function get_item_table_fields(frm) {
	const child_table = frm.fields_dict["items"];
	const child_fields = child_table.grid.docfields;

	const dialog_item_fields = child_fields.map((field) => {
		let config = {
			label: field.label,
			fieldname: field.fieldname,
			fieldtype: field.fieldtype,
			in_list_view: field.in_list_view,
			read_only: field.read_only,
			depends_on: field.depends_on,
			options: field.options,
			reqd: field.reqd,
			default: field.default,
		};

		if (field.fieldname === "qty" || field.fieldname === "rate") {
			config.onchange = function () {
				calculate_row_amount(this.grid_row);
			};
		}

		if (field.fieldname === "item_code") {
			config.onchange = function () {
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

								row.grid.refresh();
							}
						},
					});
				}
			};
		}

		if (field.fieldname === "utility_property") {
			config.in_list_view = 1;
			config.reqd = 1;
		}

		return config;
	});

	return dialog_item_fields;
}

function prepare_items_data(frm) {
	const child_table = frm.fields_dict["items"];
	const child_fields = child_table.grid.docfields;
	const allowedFields = child_fields.map((f) => f.fieldname);
	const properties = (frm.doc.requested_properties || [])
		.map((p) => p.utility_property)
		.filter(Boolean);
	return frm.doc.items.map((item) => {
		const qty = item.qty || 1;
		const rate = item.rate || 0;

		const fullData = {
			name: item.name,
			item_code: item.item_code,
			rate: rate,
			amount: flt(rate * qty),
			qty: qty,
			warehouse: item.warehouse || frappe.defaults.get_user_default("Warehouse"),
			utility_property: properties.length == 1 ? properties[0] : null,
			...item,
		};

		return Object.fromEntries(
			Object.entries(fullData).filter(([key]) => allowedFields.includes(key)),
		);
	});
}

function calculate_row_amount(row) {
	const qty = parseFloat(row.doc.qty) || 0;
	const rate = parseFloat(row.doc.rate) || 0;
	row.doc.amount = parseFloat(qty * rate);
	row.grid.refresh();
}

function configure_dialog(dialog, frm) {
	dialog.fields_dict["items_table"].grid.get_field("utility_property").get_query = function () {
		const selected_properties = frm.get_selected_utility_properties?.() || [];

		return {
			filters: {
				name: ["in", selected_properties.length ? selected_properties : ["__none"]],
			},
		};
	};

	dialog.$wrapper.find(".modal-dialog").css("max-width", "max-content");
	dialog.$wrapper.find(".modal-content").css("width", "1000px");
	dialog.show();

	const appliedStyleMap = new WeakMap();

	const observer = new MutationObserver(() => {
		const openGridRow = document.querySelector(".grid-row.grid-row-open");

		if (openGridRow && !openGridRow.classList.contains("custom-grid-modal")) {
			openGridRow.classList.add("custom-grid-modal");

			const customStyles = {
				background: "#fff",
				zIndex: "1051",
				padding: "50px",
				position: "fixed",
				top: "60px",
				left: "50%",
				transform: "translateX(-50%)",
				maxWidth: "900px",
				width: "100%",
				maxHeight: "90vh",
				overflowY: "auto",
				overflowX: "hidden",
				opacity: "1",
				pointerEvents: "auto",
				borderRadius: "8px",
			};

			appliedStyleMap.set(openGridRow, customStyles);
			Object.assign(openGridRow.style, customStyles);
		}

		document.querySelectorAll(".custom-grid-modal").forEach((el) => {
			if (!el.classList.contains("grid-row-open")) {
				el.classList.remove("custom-grid-modal");

				const appliedStyles = appliedStyleMap.get(el);
				if (appliedStyles) {
					for (const prop in appliedStyles) {
						el.style[prop] = "";
					}
					appliedStyleMap.delete(el);
				}
			}
		});
	});

	observer.observe(document.body, { childList: true, subtree: true });
}

async function showSalesDocumentModal(frm, docType, allowAdditionalRows = false) {
	const customer = await frappe.db.get_value("Customer", frm.doc.customer, ["customer_name"]);
	const today = frappe.datetime.get_today();

	const title =
		docType === "Sales Order" ? __("Create Sales Order") : __("Create Sales Invoice");

	const primaryActionMethod =
		docType === "Sales Order"
			? "utility_billing.utility_billing.doctype.utility_service_request.utility_service_request.create_sales_order_doc"
			: "utility_billing.utility_billing.doctype.utility_service_request.utility_service_request.create_sales_invoice_doc";

	const fields = [
		...get_customer_section_fields(frm, customer?.message?.customer_name),
		{
			fieldname: "transaction_details_section",
			fieldtype: "Section Break",
			label: __(""),
			collapsible: 0,
		},
		{
			fieldname: "posting_date",
			label: docType === "Sales Order" ? __("Date") : __("Posting Date"),
			fieldtype: "Date",
			default: today,
			reqd: 1,
		},
		{
			fieldname: "col_break_transaction",
			fieldtype: "Column Break",
		},
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frm.doc.company || frappe.defaults.get_user_default("Company"),
			reqd: 1,
		},
	];

	if (docType === "Sales Invoice") {
		fields.push({
			fieldname: "due_date",
			label: __("Due Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_days(today, 30),
			reqd: 1,
		});
	}

	const properties = (frm.doc.requested_properties || [])
		.map((p) => p.utility_property)
		.filter(Boolean);

	const defaultProperty = properties.length === 1 ? frm.doc.requested_properties[0] : null;

	fields.push(
		{
			fieldname: "property_auto_repeat_section",
			fieldtype: "Section Break",
			label: __(""),
			collapsible: 0,
		},
		{
			fieldname: "utility_property",
			label: __("Property"),
			fieldtype: "Link",
			options: "Utility Property",
			default: properties.length == 1 ? properties[0] : null,
			mandatory_depends_on: properties.length ? "eval:1" : "eval:0",

			get_query: () => {
				if (!properties.length) {
					return {};
				}

				return {
					filters: [["name", "in", properties]],
				};
			},

			change: function () {
				let selected_value = this.get_value();
				let items = dialog.get_value("items_table") || [];

				let property_line = null;
				if (selected_value) {
					property_line = (frm.doc.requested_properties || []).find(
						(prop) => prop.utility_property === selected_value,
					);
				}

				if (property_line) {
					if (property_line.adjustment_rule) {
						dialog.set_value("adjustment_rule", property_line.adjustment_rule);
					}
					if (property_line.end_date) {
						dialog.set_value("end_date", property_line.end_date);
					}
					items.forEach((row) => {
						row.utility_property = selected_value;
						row.frequency = property_line.frequency;
					});
				} else {
					items.forEach((row) => {
						row.utility_property = selected_value;
						row.frequency = null;
					});

					dialog.set_value("start_date", null);
					dialog.set_value("end_date", null);
				}

				dialog.set_value("items_table", items);
			},
		},
		{
			fieldname: "adjustment_rule",
			label: __("Billing Adjustment Rule"),
			fieldtype: "Link",
			options: "Billing Adjustment Rule",
			depends_on: "eval:doc.enable_auto_repeat==1",
			default: defaultProperty?.adjustment_rule,
			mandatory_depends_on: "eval:doc.enable_auto_repeat==1",
			description: __("Rule defining how billing amounts will adjust over time"),
		},
		{
			fieldname: "col_break_auto_repeat",
			fieldtype: "Column Break",
		},
		{
			fieldname: "enable_auto_repeat",
			label: __("Enable Auto Repeat"),
			fieldtype: "Check",
			default: docType === "Sales Order" ? 0 : 1,
			description: __("Enable recurring billing for this document"),
			change: function () {
				const isChecked = this.get_value();
				dialog.set_df_property("start_date", "reqd", isChecked);
				dialog.set_df_property("end_date", "reqd", isChecked);
				dialog.set_df_property("adjustment_rule", "reqd", isChecked);

				if (isChecked && dialog.get_value("utility_property")) {
					const selectedProperty = dialog.get_value("utility_property");
					const property_line = (frm.doc.requested_properties || []).find(
						(prop) => prop.utility_property === selectedProperty,
					);

					if (property_line) {
						const startDate = today;
						dialog.set_value("start_date", startDate);
					}
				} else if (!isChecked) {
					dialog.set_value("start_date", null);
					dialog.set_value("end_date", null);
				}
			},
		},
		{
			fieldname: "start_date",
			label: __("Recurring Billing Start Date"),
			fieldtype: "Date",
			default: today,
			depends_on: "eval:doc.enable_auto_repeat==1",
			mandatory_depends_on: "eval:doc.enable_auto_repeat==1",
			description: __("Date when recurring billing will begin"),
		},
		{
			fieldname: "end_date",
			label: __("Recurring Billing End Date"),
			fieldtype: "Date",
			depends_on: "eval:doc.enable_auto_repeat==1",
			default: defaultProperty?.end_date,
			description: __("Date when recurring billing will stop"),
		},
		{
			fieldname: "items_table_section",
			fieldtype: "Section Break",
			label: __(""),
			collapsible: 0,
		},
		{
			fieldname: "items_table",
			fieldtype: "Table",
			label: __("Items"),
			fields: get_item_table_fields(frm),
			data: prepare_items_data(frm),
			cannot_add_rows: !allowAdditionalRows,

			on_edit: function (row, row_modal) {
				dialog.$wrapper.addClass("frappe-modal-hidden");

				row_modal.$wrapper.css("z-index", 1052);

				row_modal.onhide = () => {
					dialog.$wrapper.removeClass("frappe-modal-hidden");
				};
			},
		},
	);

	const dialog = new frappe.ui.Dialog({
		title: title,
		fields: fields,
		primary_action_label: __("Create"),

		primary_action: function (values) {
			const items = values.items_table.map((row) => ({
				item_code: row.item_code,
				qty: row.qty,
				rate: row.rate,
				amount: row.amount,
				warehouse: row.warehouse,
				utility_property: row.utility_property,
				frequency: row.frequency,
				...row,
			}));

			const args = {
				docname: frm.doc.name,
				items: items,
				customer: values.customer,
				customer_name: values.customer_name,
				company: values.company,
				property: values.utility_property,
				enable_auto_repeat: values.enable_auto_repeat,
				adjustment_rule: values.adjustment_rule,
				start_date: values.start_date,
				end_date: values.end_date,
			};

			if (docType === "Sales Order") {
				args.transaction_date = values.posting_date;
			} else {
				args.posting_date = values.posting_date;
				args.due_date = values.due_date;
			}

			if (values.end_date && new Date(values.end_date) < new Date(values.start_date)) {
				frappe.throw(
					__(
						"Recurring Billing End Date cannot be before Recurring Billing Start Date.",
					),
				);
				return;
			}

			frappe.call({
				method: primaryActionMethod,
				args: args,
				callback: function (response) {
					dialog.hide();
					if (response.message) {
						frappe.show_alert({
							message: `${docType} created successfully!`,
							indicator: "green",
						});
						frappe.set_route("Form", docType, response.message);
					}
				},
			});
		},
	});

	configure_dialog(dialog, frm);
}

async function addActionButtons(frm) {
	const currentStatus = frm.doc.request_status;

	const settings = await frappe.db.get_doc(settingsDoctypeName, settingsDoctypeName);

	const enableExtraRows = settings?.enable_extra_rows_for_sosi_creation == 1 ? true : false;

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
				__("Create"),
			);
		} else {
			const contract = await frappe.db.get_value(
				"Contract",
				{ utility_service_request: frm.doc.name, docstatus: 1 },
				"name",
			);

			const deposit = await frappe.db.get_value(
				"Sales Order",
				{ utility_service_request: frm.doc.name, docstatus: 1 },
				"name",
			);

			const contractName = contract?.message?.name || null;
			const depositName = deposit?.message?.name || null;
			const canCreateContract =
				!contractName &&
				(!settings?.require_deposit_before_contract_creation || depositName);

			if (settings?.rent_billing_approach === "Item Price") {
				frm.add_custom_button(
					__("Item Prices"),
					function () {
						showItemPriceScheduleModal(frm);
					},
					__("Define"),
				);
			}

			frm.add_custom_button(
				__("Sales Order / Deposit"),
				function () {
					showSalesDocumentModal(frm, "Sales Order", enableExtraRows);
				},
				__("Create"),
			);

			if (canCreateContract) {
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
					__("Create"),
				);
			}
			if (
				(settings?.require_contract_before_sales_invoice_creation && contractName) ||
				!settings?.require_contract_before_sales_invoice_creation
			) {
				frm.add_custom_button(
					__("Sales Invoice"),
					function () {
						showSalesDocumentModal(frm, "Sales Invoice", enableExtraRows);
					},
					__("Create"),
				);
			}
		}
	}

	if (currentStatus === "" && settings?.enable_site_survey == 1) {
		frm.add_custom_button(
			__("Site Survey"),
			function () {
				frappe.call({
					method: "utility_billing.utility_billing.doctype.utility_service_request.utility_service_request.get_site_survey_defaults",
					args: {
						docname: frm.doc.name,
					},
					callback: function (r) {
						if (!r.message) return;

						frappe.new_doc("Issue", r.message);
					},
				});
			},
			__("Create"),
		);
	} else if (currentStatus === "Site Survey Completed" && settings?.enable_site_survey == 1) {
		frm.add_custom_button(
			__("BOM"),
			async function () {
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
					secondary_action: async function () {
						const selected_bom = dialog.get_value("selected_bom");
						if (selected_bom) {
							try {
								const response = await frappe.call({
									method: "utility_billing.utility_billing.doctype.utility_service_request.utility_service_request.bom_new_version",
									args: {
										bom: selected_bom,
									},
								});

								if (response && response.message) {
									const new_bom = response.message;
									new_bom.utility_service_request = frm.doc.name;
									const doc = await frappe.db.insert(new_bom);
									frappe.set_route("Form", "BOM", doc.name);
								}
							} catch (err) {
								frappe.msgprint({
									title: __("Error"),
									message: __("Failed to save the BOM: ") + err.message,
									indicator: "red",
								});
							}
						} else {
							frappe.msgprint(__("Please select a BOM to create a new version."));
						}
					},
				});

				dialog.show();
			},
			__("Create"),
		);
	}
}

function handle_response(response, actionLabel, frm) {
	if (response.message) {
		frappe.show_alert({ message: `${actionLabel} created successfully!`, indicator: "green" });
		frm.reload_doc();
	} else {
		frappe.show_alert({ message: `Error while creating ${actionLabel}!`, indicator: "red" });
	}
}

/**
 * Child table columns of the generated rate table.
 *
 * ``base_rate`` is the only editable column: it is the starting rate the user
 * enters, while the remaining columns are filled in by the preview.
 */
/**
 * Child table columns of the generated rate table.
 *
 * Only From, To and Rate are shown: the starting rate, increment count,
 * property and item are constant for the selected property and already
 * visible in the fields above. ``base_rate`` and ``rate`` stay editable so the
 * generated schedule can be corrected by hand; dates stay read-only because
 * they define the periods.
 */
function get_item_price_schedule_fields() {
	return [
		{
			fieldname: "valid_from",
			fieldtype: "Date",
			label: __("From"),
			in_list_view: 1,
			read_only: 1,
		},
		{
			fieldname: "valid_upto",
			fieldtype: "Date",
			label: __("To"),
			in_list_view: 1,
			read_only: 1,
		},
		{ fieldname: "rate", fieldtype: "Currency", label: __("Rate"), in_list_view: 1, reqd: 1 },
		{
			fieldname: "base_rate",
			fieldtype: "Currency",
			label: __("Starting Rate"),
			read_only: 1,
		},
		{ fieldname: "increment_count", fieldtype: "Int", label: __("Increments"), read_only: 1 },
		{
			fieldname: "property",
			fieldtype: "Link",
			options: "Utility Property",
			label: __("Property"),
			read_only: 1,
		},
		{
			fieldname: "item_code",
			fieldtype: "Link",
			options: "Item",
			label: __("Item"),
			read_only: 1,
		},
	];
}

/**
 * Manual increment settings entered in the modal.
 *
 * Blank values are omitted so the Billing Adjustment Rule keeps providing them.
 */
function get_increment_values(dialog) {
	const fields = [
		"increment_interval_months",
		"increment_percentage",
		"effective_after_months",
		"adjustment_basis",
	];
	const increment = {};

	const mapped = {
		increment_interval_months: "interval_months",
		increment_percentage: "percentage",
		effective_after_months: "effective_after_months",
		adjustment_basis: "basis",
	};

	fields.forEach((field) => {
		const value = dialog.get_value(field);
		if (value !== undefined && value !== null && value !== "") {
			increment[mapped[field]] = value;
		}
	});

	return increment;
}

/**
 * Copy the increment settings of a Billing Adjustment Rule into the modal.
 *
 * The rule acts as the starting point; every field stays editable afterwards
 * and the schedule is recalculated once the values are applied.
 */
function apply_rule_defaults(dialog, rule_name) {
	if (!rule_name) return;

	frappe.db.get_doc("Billing Adjustment Rule", rule_name).then((rule) => {
		dialog._suppress_auto_preview = true;

		dialog.set_value("frequency", rule.frequency || "Monthly");
		dialog.set_value("increment_interval_months", rule.increment_interval_months);
		dialog.set_value("increment_percentage", rule.increment_percentage);
		dialog.set_value("effective_after_months", rule.effective_after_months);
		dialog.set_value("adjustment_basis", rule.adjustment_basis || "Original Amount");

		dialog._suppress_auto_preview = false;
		schedule_auto_preview(dialog, dialog._frm);
	});
}

/**
 * Requested properties of the service request that can be priced.
 */
function get_requested_properties(frm) {
	return (frm.doc.requested_properties || [])
		.map((property) => property.utility_property)
		.filter(Boolean);
}

/**
 * The rate row of the property currently selected in the modal.
 *
 * Used to read the service item the schedule belongs to.
 */
function get_property_row(dialog, property) {
	return (dialog.get_value("rates_table") || []).find((row) => row.property === property);
}

/**
 * Starting rates entered so far, keyed by property.
 *
 * Kept outside the schedule table because that table only holds generated
 * periods; a synthetic "rate holder" row would be indistinguishable from a
 * real period.
 */
function remember_base_rate(dialog, property, rate) {
	dialog._base_rates = dialog._base_rates || {};
	dialog._base_rates[property] = rate;
}

/**
 * The starting rate recorded for a property, or ``null`` when unset.
 */
function get_base_rate(dialog, property) {
	const rate = (dialog._base_rates || {})[property];

	return rate === undefined ? null : rate;
}

/**
 * Record the starting rate entered for the selected property.
 */
function set_property_rate(dialog, property, rate) {
	remember_base_rate(dialog, property, rate);
}

/**
 * Replace the rows of the schedule table.
 *
 * Frappe's grid reads its rows from ``df.data`` when the table lives in a
 * dialog (``get_data()`` falls back to it because there is no ``frm``), so the
 * rows are written there and the grid refreshed.
 *
 * Each row also needs the ``name`` and ``idx`` bookkeeping fields the grid
 * uses to key its rows; without them the rows are filtered out and the table
 * renders empty even though the data is present.
 */
function set_schedule_table_rows(dialog, rows) {
	const field = dialog.get_field("rates_table");
	if (!field) return;

	const to_stored_date = (value) => {
		if (!value) return value;
		if (value instanceof Date) return frappe.datetime.obj_to_str(value).slice(0, 10);

		return String(value).slice(0, 10);
	};

	const normalised = rows.map((row, index) => ({
		...row,
		name: row.name || frappe.utils.get_random(10),
		idx: index + 1,
		doctype: "Rates",
		valid_from: to_stored_date(row.valid_from),
		valid_upto: to_stored_date(row.valid_upto),
	}));

	field.df.data = normalised;
	dialog.set_value("rates_table", normalised);
	field.grid.refresh();
}

/**
 * Drop the schedule rows of a property, keeping other properties' rows.
 */
function clear_property_schedule(dialog, property) {
	const others = (dialog.get_value("rates_table") || []).filter(
		(candidate) => candidate.property !== property,
	);

	dialog._suppress_auto_preview = true;
	set_schedule_table_rows(dialog, others);
	dialog._suppress_auto_preview = false;
	delete (dialog._cached_rates || {})[property];
}

/**
 * Show the rates generated for the selected property only.
 *
 * Only real generated periods are written to the table, so nothing in it can
 * be mistaken for a schedule row. The periods are cached per property so
 * switching back and forth restores the last edited schedule.
 */
function show_property_schedule(dialog, property, periods) {
	const row = get_property_row(dialog, property);
	const item_code = row?.item_code || null;
	const base_rate = get_base_rate(dialog, property);

	dialog._cached_rates = dialog._cached_rates || {};
	dialog._cached_rates[property] = periods;
	remember_generated_rates(dialog, property, periods);

	// Keep only rows of earlier properties so a different property's schedule
	// is never shown alongside this one.
	const others = (dialog.get_value("rates_table") || []).filter(
		(candidate) => candidate.property !== property && candidate.valid_from,
	);

	const rows = [
		...others,
		...periods.map((period) => ({
			property,
			item_code,
			base_rate,
			increment_count: period.increment_count,
			valid_from: period.valid_from,
			valid_upto: period.valid_upto,
			rate: period.rate,
		})),
	];

	dialog._suppress_auto_preview = true;
	set_schedule_table_rows(dialog, rows);
	dialog._suppress_auto_preview = false;
}

/**
 * Switch the modal to a property and load its saved starting rate.
 *
 * Any rates previously generated for the property are restored so switching
 * back and forth never loses work or manual edits.
 */
function select_property(dialog, frm, property) {
	if (!property) return;

	const previous = dialog.get_value("_selected_property");
	if (previous && previous !== property) {
		set_property_rate(dialog, previous, dialog.get_value("starting_rate"));
	}

	dialog._suppress_auto_preview = true;
	dialog.set_value("starting_rate", get_base_rate(dialog, property));
	set_schedule_table_rows(dialog, []);
	dialog._suppress_auto_preview = false;

	dialog._selected_property = property;

	const cached = dialog._cached_rates?.[property];
	if (cached) {
		show_property_schedule(dialog, property, cached);
		return;
	}

	schedule_auto_preview(dialog, frm);
}

/**
 * Schedule an automatic preview of the selected property.
 *
 * Field changes fire in bursts (a rule fills six fields at once), so the call
 * is debounced and any in-flight request is discarded when superseded.
 */
function schedule_auto_preview(dialog, frm) {
	clearTimeout(dialog._preview_timer);
	dialog._preview_timer = setTimeout(() => {
		if (dialog._suppress_auto_preview) return;
		preview_item_price_schedule(dialog, frm, { silent: true });
	}, 350);
}

/**
 * Keep the per-property starting rate in sync with the edited table.
 *
 * When a user retypes the first period's rate, that becomes the new starting
 * rate for the property so the whole schedule can be regenerated from it.
 */
function sync_rates_from_table(dialog) {
	const property = dialog.get_value("utility_property");
	if (!property) return;

	const first_period = (dialog.get_value("rates_table") || [])
		.filter((entry) => entry.property === property && entry.valid_from)
		.sort((a, b) => (a.valid_from < b.valid_from ? -1 : 1))[0];

	if (first_period && first_period.rate !== undefined && first_period.rate !== null) {
		dialog._suppress_auto_preview = true;
		dialog.set_value("starting_rate", first_period.rate);
		dialog._suppress_auto_preview = false;
	}
}

/**
 * Report the state of the preview above the schedule table.
 *
 * The message is rendered as plain text so formatted values such as
 * "Sh 6,000.00" can never leak markup into the field.
 */
function set_preview_status(dialog, message, indicator = "muted") {
	const field = dialog.get_field("preview_status");
	if (!field) return;

	const line = $(`<div class="small"></div>`)
		.addClass(`text-${indicator}`)
		.css("padding-top", "6px")
		.text(message);

	field.$wrapper.empty().append(line);
}

/**
 * Rates the user changed in the schedule table.
 *
 * Every period whose rate differs from what the backend generated is sent
 * back as an override, so edits survive a recalculation triggered by another
 * field change. The table is the only place rates are edited.
 */
function get_edited_rate_rows(dialog, property) {
	const generated = (dialog._generated_rates || {})[property] || {};
	const edited = [];

	(dialog.get_value("rates_table") || [])
		.filter((row) => row.property === property && row.valid_from)
		.forEach((row) => {
			const original = generated[row.valid_from];
			if (original === undefined || flt(row.rate) === flt(original)) return;

			edited.push({ from_date: row.valid_from, rate: row.rate });
		});

	return edited;
}

/**
 * Record the rates the backend generated so manual edits can be detected.
 */
function remember_generated_rates(dialog, property, periods) {
	dialog._generated_rates = dialog._generated_rates || {};
	dialog._generated_rates[property] = Object.fromEntries(
		periods.map((period) => [period.valid_from, flt(period.rate)]),
	);
}

/**
 * Show how many properties still need prices.
 */
function report_progress(dialog, properties) {
	const done = Object.keys(dialog._created_properties || {});
	const pending = properties.filter((name) => !done.includes(name));

	if (!done.length) return;

	frappe.show_alert({
		message: __("{0} of {1} properties priced. {2} remaining.", [
			done.length,
			properties.length,
			pending.length,
		]),
		indicator: pending.length ? "blue" : "green",
	});
}

/**
 * Load the Item Prices created for this request into the HTML summary field.
 *
 * The Item Prices are the source of truth for the schedule, so the field is
 * rendered from them rather than from a stored copy.
 */
function load_item_price_summary(frm) {
	const field = frm.get_field("item_price_summary");
	if (!field || frm.is_new()) return;

	field.$wrapper.html("<div class='text-muted'>Loading Item Prices...</div>");

	frappe.call({
		method: "utility_billing.utility_billing.utils.item_price_actions.get_item_price_summary",
		args: { docname: frm.doc.name },
		callback: function (response) {
			if (!response.message) return;

			field.$wrapper.html(response.message.html);
		},
	});
}

/**
 * Widen the dialog so the schedule tables can use several columns.
 *
 * A fixed width is used instead of the stock "large" size because the modal
 * shows two tables and needs the extra horizontal room to keep the height
 * down.
 */
function make_dialog_wide(dialog, width = "92vw") {
	dialog.$wrapper.find(".modal-dialog").css({ "max-width": width, width: width });
}

function showItemPriceScheduleModal(frm) {
	const properties = get_requested_properties(frm);

	if (!properties.length) {
		frappe.msgprint(__("Please add at least one property to define item prices."));
		return;
	}

	const dialog = new frappe.ui.Dialog({
		title: __("Define Item Prices"),
		size: "large",
		fields: [
			{
				fieldname: "utility_property",
				fieldtype: "Link",
				options: "Utility Property",
				label: __("Property"),
				reqd: 1,
				get_query: () => ({ filters: { name: ["in", properties] } }),
				change: function () {
					select_property(dialog, frm, this.get_value());
				},
			},
			{
				fieldname: "starting_rate",
				fieldtype: "Currency",
				label: __("Starting Rate"),
				description: __("Rent for the first period."),
				change: function () {
					const property = dialog.get_value("utility_property");
					if (property) {
						set_property_rate(dialog, property, this.get_value());
						schedule_auto_preview(dialog, frm);
					}
				},
			},
			{
				fieldname: "customer",
				fieldtype: "Link",
				options: "Customer",
				label: __("Customer"),
				default: frm.doc.customer,
				description: __("Blank prices for all customers."),
			},
			{
				fieldname: "column_break_period",
				fieldtype: "Column Break",
			},
			{
				fieldname: "start_date",
				fieldtype: "Date",
				label: __("Lease Start"),
				default: frm.doc.start_date || frappe.datetime.get_today(),
				reqd: 1,
				change: () => schedule_auto_preview(dialog, frm),
			},
			{
				fieldname: "end_date",
				fieldtype: "Date",
				label: __("Lease End"),
				default: frm.doc.end_date,
				change: () => schedule_auto_preview(dialog, frm),
			},
			{
				fieldname: "price_list",
				fieldtype: "Link",
				options: "Price List",
				label: __("Price List"),
				default: frm.doc.price_list,
				reqd: 1,
				change: () => schedule_auto_preview(dialog, frm),
			},
			{
				fieldname: "increment_section",
				fieldtype: "Section Break",
				label: __("Increments"),
				description: __(
					"Pick a Billing Adjustment Rule to fill these in, or set them manually. Rates recalculate automatically.",
				),
			},
			{
				fieldname: "adjustment_rule",
				fieldtype: "Link",
				options: "Billing Adjustment Rule",
				label: __("Billing Adjustment Rule"),
				description: __("Optional. Fills the fields below."),
				change: function () {
					apply_rule_defaults(dialog, this.get_value());
				},
			},
			{
				fieldname: "frequency",
				fieldtype: "Select",
				options: "\nDaily\nWeekly\nMonthly\nQuarterly\nHalf-yearly\nYearly",
				label: __("Frequency"),
				default: "Monthly",
				description: __("How often rent is billed."),
				change: () => schedule_auto_preview(dialog, frm),
			},
			{
				fieldname: "increment_interval_months",
				fieldtype: "Float",
				label: __("Every (Months)"),
				default: 12,
				description: __("Months between increments."),
				change: () => schedule_auto_preview(dialog, frm),
			},
			{
				fieldname: "increment_percentage",
				fieldtype: "Percent",
				label: __("Increase By (%)"),
				default: 0,
				change: () => schedule_auto_preview(dialog, frm),
			},
			{
				fieldname: "column_break_increment",
				fieldtype: "Column Break",
			},
			{
				fieldname: "adjustment_basis",
				fieldtype: "Select",
				options: "Original Amount\nLast Adjusted Amount",
				label: __("Based On"),
				default: "Original Amount",
				description: __("Original grows linearly; Last Adjusted compounds."),
				change: () => schedule_auto_preview(dialog, frm),
			},
			{
				fieldname: "effective_after_months",
				fieldtype: "Float",
				label: __("Start After (Months)"),
				default: 0,
				description: __("Months before the first increment."),
				change: () => schedule_auto_preview(dialog, frm),
			},
			{
				fieldname: "replace_existing",
				fieldtype: "Check",
				label: __("Replace Existing Prices"),
				default: 0,
				description: __("Delete prices previously generated for this item first."),
			},
			{
				fieldname: "rates_section",
				fieldtype: "Section Break",
				label: __("Schedule"),
			},
			{
				fieldname: "preview_status",
				fieldtype: "HTML",
				options: "<div class='text-muted small'></div>",
			},
			{
				fieldname: "rates_table",
				fieldtype: "Table",
				label: __("Rates"),
				data: [],
				fields: get_item_price_schedule_fields(),
				on_edit: function (row, row_modal) {
					row_modal.onhide = () => {
						sync_rates_from_table(dialog);
						schedule_auto_preview(dialog, frm);
					};
				},
			},
		],
		primary_action_label: __("Create Item Prices"),
		primary_action: function (values) {
			const property = values.utility_property || dialog.get_value("utility_property");

			if (!property) {
				frappe.msgprint(__("Please select a property."));
				return;
			}

			if (get_selected_rate(dialog) === null) {
				frappe.msgprint(__("Please enter the starting rate for {0}.", [property]));
				return;
			}

			frappe.call({
				method: "utility_billing.utility_billing.utils.item_price_actions.create_item_price_schedule",
				args: {
					...build_schedule_args(dialog, frm, values),
					replace_existing: values.replace_existing ? 1 : 0,
				},
				freeze: true,
				freeze_message: __("Creating Item Prices..."),
				callback: function (response) {
					if (!response.message) return;

					dialog._created_properties = dialog._created_properties || {};
					dialog._created_properties[property] = true;

					frappe.show_alert({
						message: __("{0}: {1} Item Prices created, {2} periods already priced.", [
							property,
							response.message.created_count,
							response.message.skipped,
						]),
						indicator: "green",
					});

					load_item_price_summary(frm);
					report_progress(dialog, properties);

					const pending = properties.filter((name) => !dialog._created_properties[name]);

					if (!pending.length) {
						dialog.hide();
						return;
					}

					dialog.set_value("utility_property", pending[0]);
					select_property(dialog, frm, pending[0]);
				},
			});
		},
		secondary_action_label: __("Refresh Preview"),
		secondary_action: function () {
			preview_item_price_schedule(dialog, frm);
		},
	});

	dialog._frm = frm;

	const first_property = properties[0];
	dialog.set_value("utility_property", first_property);
	select_property(dialog, frm, first_property);

	const default_property = (frm.doc.requested_properties || []).find(
		(property) => property.utility_property && property.adjustment_rule,
	);
	if (default_property) {
		dialog.set_value("adjustment_rule", default_property.adjustment_rule);
		apply_rule_defaults(dialog, default_property.adjustment_rule);
	}

	dialog.show();
	report_progress(dialog, properties);
	dialog.$wrapper.on("shown.bs.modal", () => {
		watch_schedule_table_edits(dialog, frm);
		schedule_auto_preview(dialog, frm);
	});
}

/**
 * Recalculate the schedule when a rate is edited directly in the table.
 *
 * The grid is refreshed on every keystroke, so the handler is debounced to
 * avoid a request per character.
 */
function watch_schedule_table_edits(dialog, frm) {
	const grid = dialog.fields_dict.rates_table?.grid;
	if (!grid) return;

	const handler = () => {
		clearTimeout(dialog._table_edit_timer);
		dialog._table_edit_timer = setTimeout(() => {
			sync_rates_from_table(dialog);
			schedule_auto_preview(dialog, frm);
		}, 600);
	};

	// Inline edits bubble up as `change` on the grid inputs; edits made in the
	// row modal are handled by the table's `on_edit` callback.
	grid.wrapper.on("change", "input", handler);
}

/**
 * The starting rate currently selected in the modal, or ``null`` when unset.
 */
function get_selected_rate(dialog) {
	const rate = dialog.get_value("starting_rate");

	return rate === undefined || rate === null || rate === "" ? null : rate;
}

/**
 * Build the request arguments shared by the preview and create actions.
 *
 * Only the selected property is sent, so each property is priced with its own
 * starting rate. The increment fields are always sent, so whatever the modal
 * currently shows is what the backend applies, even when a Billing Adjustment
 * Rule supplied them.
 */
function build_schedule_args(dialog, frm, values) {
	const property = dialog.get_value("utility_property");
	const base_rates = {};

	base_rates[property] = get_selected_rate(dialog);

	return {
		docname: frm.doc.name,
		properties: [property],
		base_rates,
		start_date: values.start_date,
		end_date: values.end_date || null,
		price_list: values.price_list,
		customer: values.customer || null,
		adjustment_rule: values.adjustment_rule || null,
		frequency: values.frequency || null,
		increment: get_increment_values(dialog),
		overrides: get_edited_rate_rows(dialog, property),
	};
}

/**
 * Recalculate the schedule of the selected property.
 *
 * Runs automatically whenever a relevant field changes, and on demand from the
 * Preview button. Rates the user edited by hand are sent back as overrides so
 * they survive the recalculation.
 *
 * Args:
 *     silent: When true, missing inputs do not raise a message because the
 *         user is still filling the form in.
 */
function preview_item_price_schedule(dialog, frm, { silent = false } = {}) {
	const property = dialog.get_value("utility_property");

	if (!dialog.get_value("start_date")) {
		if (!silent) frappe.msgprint(__("Please set the lease start date before previewing."));
		return;
	}

	if (!property) {
		if (!silent) frappe.msgprint(__("Please select a property."));
		return;
	}

	if (get_selected_rate(dialog) === null) {
		set_preview_status(dialog, __("Enter a starting rate to see the schedule."), "muted");
		return;
	}

	const request_id = (dialog._preview_request_id || 0) + 1;
	dialog._preview_request_id = request_id;
	set_preview_status(dialog, __("Calculating schedule..."), "muted");

	frappe.call({
		method: "utility_billing.utility_billing.utils.item_price_actions.preview_item_price_schedule",
		args: build_schedule_args(dialog, frm, dialog.get_values()),
		callback: function (response) {
			// A newer preview was requested while this one was in flight.
			if (dialog._preview_request_id !== request_id) return;

			if (!response.message || !response.message.length) {
				clear_property_schedule(dialog, property);
				set_preview_status(dialog, __("No schedule could be generated."), "danger");
				return;
			}

			const periods = response.message[0].periods;
			show_property_schedule(dialog, property, periods);
			report_schedule_summary(
				dialog,
				property,
				periods,
				get_edited_rate_rows(dialog, property).length,
			);
		},
		error: function () {
			if (dialog._preview_request_id !== request_id) return;

			clear_property_schedule(dialog, property);
			set_preview_status(dialog, __("Could not generate the schedule."), "danger");
		},
	});
}

/**
 * Describe the generated schedule above the table.
 */
function report_schedule_summary(dialog, property, periods, edited_count) {
	if (!periods.length) {
		set_preview_status(dialog, __("No periods generated."), "muted");
		return;
	}

	const first = periods[0];
	const last = periods[periods.length - 1];
	const format_rate = (rate) => flt(rate).toLocaleString();

	const message = __("{0} periods from {1} to {2}. First rate {3}, last rate {4}.", [
		periods.length,
		frappe.datetime.str_to_user(first.valid_from),
		frappe.datetime.str_to_user(last.valid_upto),
		format_rate(first.rate),
		format_rate(last.rate),
	]);

	set_preview_status(
		dialog,
		edited_count ? `${message} ${__("{0} rate(s) edited by hand.", [edited_count])}` : message,
		"muted",
	);
}
