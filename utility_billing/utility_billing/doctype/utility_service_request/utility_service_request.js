const settingsDoctypeName = "Utility Billing Settings";

frappe.ui.form.on("Utility Service Request", {
	refresh: async function (frm) {
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

		frm.fields_dict["utility_bill_structure"].get_query = function () {
			return {
				filters: {
					company: frm.doc.company || frappe.defaults.get_user_default("Company"),
				},
			};
		};
		frm.fields_dict["utility_property"].get_query = function () {
			return {
				filters: {
					is_group: 1,
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

		// Function to get selected utility_property values
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
							contract_template.requires_fulfilment
						);

						if (frm.doc.requires_fulfilment) {
							// Populate the fulfilment terms table from a contract template, if any
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
				frm.doc.contract_length_months
			);
		}
	},
	start_date: (frm, cdt, cdn) => update_child_contract_fields(frm, cdt, cdn, "start_date"),
	end_date: (frm, cdt, cdn) => update_child_contract_fields(frm, cdt, cdn, "end_date"),
	contract_length_months: (frm, cdt, cdn) =>
		update_child_contract_fields(frm, cdt, cdn, "contract_length_months"),
});

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

// Common function to get customer section fields with 2 columns
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
			fieldname: "col_break_customer", // Column Break for 2 columns
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

// Common function to get item table fields configuration dynamically from the form
function get_item_table_fields(frm) {
	const child_table = frm.fields_dict["items"];
	const child_fields = child_table.grid.docfields;

	// Filter and map fields with custom logic
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

		// Add onchange handlers
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
								// Note: refresh_field("items_table") might not work directly on dialog table.
								// You might need to refresh the grid if it's a custom table.
								row.grid.refresh();
							}
						},
					});
				}
			};
		}

		// Ensure utility_property is visible in the list view
		if (field.fieldname === "utility_property") {
			config.in_list_view = 1;
			config.reqd = 1;
		}

		return config;
	});

	return dialog_item_fields;
}

// Common function to prepare items data dynamically based on allowed fields
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

		// Original data with only the necessary fields
		const fullData = {
			name: item.name,
			item_code: item.item_code,
			rate: rate,
			amount: flt(rate * qty),
			qty: qty,
			warehouse: item.warehouse || frappe.defaults.get_user_default("Warehouse"),
			utility_property: properties.length == 1 ? properties[0] : null,
			...item, // Include all other fields from the original item
		};

		// Filter out fields not in child table fields
		return Object.fromEntries(
			Object.entries(fullData).filter(([key]) => allowedFields.includes(key))
		);
	});
}

// Common function to calculate row amount
function calculate_row_amount(row) {
	const qty = parseFloat(row.doc.qty) || 0;
	const rate = parseFloat(row.doc.rate) || 0;
	row.doc.amount = parseFloat(qty * rate);
	row.grid.refresh();
}

// Common function to configure dialog properties
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
	// Fetch customer details to pre-fill the dialog
	const customer = await frappe.db.get_value("Customer", frm.doc.customer, ["customer_name"]);
	const today = frappe.datetime.get_today(); // Get today's date

	// Determine the title of the dialog based on document type
	const title =
		docType === "Sales Order" ? __("Create Sales Order") : __("Create Sales Invoice");
	// Determine the primary action method to call on form submission
	const primaryActionMethod =
		docType === "Sales Order"
			? "utility_billing.utility_billing.doctype.utility_service_request.utility_service_request.create_sales_order_doc"
			: "utility_billing.utility_billing.doctype.utility_service_request.utility_service_request.create_sales_invoice_doc";

	// Define the fields for the dialog
	const fields = [
		...get_customer_section_fields(frm, customer?.message?.customer_name), // Customer-related fields
		{
			fieldname: "transaction_details_section",
			fieldtype: "Section Break",
			label: __(""),
			collapsible: 0,
		},
		{
			fieldname: "posting_date", // Use posting_date for both for consistency, label will change
			label: docType === "Sales Order" ? __("Date") : __("Posting Date"),
			fieldtype: "Date",
			default: today,
			reqd: 1,
		},
		{
			fieldname: "col_break_transaction", // Column Break for 2 columns in transaction details
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

	// Add due_date field specifically for Sales Invoice
	if (docType === "Sales Invoice") {
		fields.push({
			fieldname: "due_date",
			label: __("Due Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_days(today, 30), // Default due date to 30 days from today
			reqd: 1,
		});
	}

	const properties = (frm.doc.requested_properties || [])
		.map((p) => p.utility_property)
		.filter(Boolean);

	const defaultProperty = properties.length === 1 ? frm.doc.requested_properties[0] : null;

	// Add fields for Property and Auto Repeat settings
	fields.push(
		{
			fieldname: "property_auto_repeat_section", // New section for Property and Auto Repeat
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
			// Custom query to filter properties based on `requested_properties` in the parent form
			get_query: () => {
				// If no properties in requested_properties, don't filter
				if (!properties.length) {
					return {};
				}

				return {
					filters: [["name", "in", properties]],
				};
			},
			// Logic to execute when the utility_property field changes
			change: function () {
				let selected_value = this.get_value(); // Get the currently selected property
				let items = dialog.get_value("items_table") || []; // Get current items in the table

				let property_line = null;
				if (selected_value) {
					// Find the corresponding property line in the parent form's requested_properties
					property_line = (frm.doc.requested_properties || []).find(
						(prop) => prop.utility_property === selected_value
					);
				}

				// Update items with property and frequency if a matching property line is found
				if (property_line) {
					if (property_line.adjustment_rule) {
						dialog.set_value("adjustment_rule", property_line.adjustment_rule);
					}
					if (property_line.end_date) {
						dialog.set_value("end_date", property_line.end_date);
					}
					items.forEach((row) => {
						row.utility_property = selected_value;
						row.frequency = property_line.frequency; // Set frequency from property line

						// Set adjustment_rule if it exists in the property line
					});
				} else {
					// Clear property and frequency from items if no matching property line
					items.forEach((row) => {
						row.utility_property = selected_value;
						row.frequency = null;
					});
					// Clear auto-repeat dates if no property is selected or matched
					dialog.set_value("start_date", null);
					dialog.set_value("end_date", null);
				}

				dialog.set_value("items_table", items); // Update the items table in the dialog
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
			fieldname: "col_break_auto_repeat", // Column Break for 2 columns in this new section
			fieldtype: "Column Break",
		},
		{
			fieldname: "enable_auto_repeat",
			label: __("Enable Auto Repeat"),
			fieldtype: "Check",
			default: docType === "Sales Order" ? 0 : 1,
			description: __("Enable recurring billing for this document"),
			change: function () {
				// When enable_auto_repeat changes, update the visibility and mandatory status of date fields
				const isChecked = this.get_value();
				dialog.set_df_property("start_date", "reqd", isChecked);
				dialog.set_df_property("end_date", "reqd", isChecked);
				dialog.set_df_property("adjustment_rule", "reqd", isChecked);

				// If enabled, and a property is selected, auto-set start date
				if (isChecked && dialog.get_value("utility_property")) {
					const selectedProperty = dialog.get_value("utility_property");
					const property_line = (frm.doc.requested_properties || []).find(
						(prop) => prop.utility_property === selectedProperty
					);

					if (property_line) {
						const startDate = today;
						dialog.set_value("start_date", startDate);
						// No automatic end date calculation without calculateEndDate
					}
				} else if (!isChecked) {
					// If disabled, clear the dates
					dialog.set_value("start_date", null);
					dialog.set_value("end_date", null);
				}
			},
		},
		{
			fieldname: "start_date",
			label: __("Recurring Billing Start Date"),
			fieldtype: "Date",
			default: today, // Default start date to today
			depends_on: "eval:doc.enable_auto_repeat==1", // Only show if auto-repeat is enabled
			mandatory_depends_on: "eval:doc.enable_auto_repeat==1", // Mandatory if auto-repeat is enabled
			description: __("Date when recurring billing will begin"),
		},
		{
			fieldname: "end_date",
			label: __("Recurring Billing End Date"),
			fieldtype: "Date",
			depends_on: "eval:doc.enable_auto_repeat==1", // Only show if auto-repeat is enabled
			default: defaultProperty?.end_date,
			mandatory_depends_on: "eval:doc.enable_auto_repeat==1", // Mandatory if auto-repeat is enabled
			description: __("Date when recurring billing will stop"),
		},
		{
			fieldname: "items_table_section", // New section for Items Table
			fieldtype: "Section Break",
			label: __(""),
			collapsible: 0,
		},
		{
			fieldname: "items_table",
			fieldtype: "Table",
			label: __("Items"),
			fields: get_item_table_fields(frm), // Get item table field definitions
			data: prepare_items_data(frm), // Prepare initial data for the item table
			cannot_add_rows: !allowAdditionalRows, // Prevent adding rows if not allowed
			// Custom handler for when a row in the table is edited (opens a row modal)
			on_edit: function (row, row_modal) {
				// Hide parent dialog temporarily to avoid overlap
				dialog.$wrapper.addClass("frappe-modal-hidden");

				// Ensure row modal has a higher z-index to be on top
				row_modal.$wrapper.css("z-index", 1052);

				// On close of the row modal, show the parent dialog again
				row_modal.onhide = () => {
					dialog.$wrapper.removeClass("frappe-modal-hidden");
				};
			},
		}
	);

	// Create a new Frappe UI Dialog instance
	const dialog = new frappe.ui.Dialog({
		title: title,
		fields: fields,
		primary_action_label: __("Create"),
		// Primary action to be executed when the "Create" button is clicked
		primary_action: function (values) {
			// Map table data to the required format for the API call
			const items = values.items_table.map((row) => ({
				// Include all necessary fields from the dialog item rows
				item_code: row.item_code,
				qty: row.qty,
				rate: row.rate,
				amount: row.amount,
				warehouse: row.warehouse,
				utility_property: row.utility_property,
				frequency: row.frequency, // Ensure frequency is passed if applicable
				...row, // Include any other relevant fields from the item table
			}));

			// Prepare arguments for the API call
			const args = {
				docname: frm.doc.name, // Parent document name
				items: items,
				customer: values.customer,
				customer_name: values.customer_name,
				company: values.company,
				property: values.utility_property, // Pass the selected property
				enable_auto_repeat: values.enable_auto_repeat, // Pass the checkbox value
				adjustment_rule: values.adjustment_rule, // Pass the adjustment rule if auto repeat is enabled
				start_date: values.start_date, // Pass the start date
				end_date: values.end_date, // Pass the end date
			};

			// Add transaction-specific dates based on document type
			if (docType === "Sales Order") {
				args.transaction_date = values.posting_date;
			} else {
				args.posting_date = values.posting_date;
				args.due_date = values.due_date;
			}

			if (values.end_date && new Date(values.end_date) < new Date(values.start_date)) {
				frappe.throw(
					__("Recurring Billing End Date cannot be before Recurring Billing Start Date.")
				);
				return;
			}

			// Make the API call to create the document
			frappe.call({
				method: primaryActionMethod,
				args: args,
				callback: function (response) {
					dialog.hide(); // Hide the dialog after the call
					if (response.message) {
						// Show success message and navigate to the newly created document
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

	// Configure the dialog after initialization (e.g., initial field visibility)
	configure_dialog(dialog, frm);
}

// Update the action buttons to use the new common modal function
async function addActionButtons(frm) {
	const currentStatus = frm.doc.request_status;

	const settings = await frappe.db.get_doc(settingsDoctypeName, settingsDoctypeName);

	const enableExtraRows = settings?.enable_extra_rows_for_sosi_creation == 1 ? true : false;

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
			const contract = await frappe.db.get_value(
				"Contract",
				{ utility_service_request: frm.doc.name, docstatus: 1 },
				"name"
			);

			const deposit = await frappe.db.get_value(
				"Sales Order",
				{ utility_service_request: frm.doc.name, docstatus: 1 },
				"name"
			);

			const contractName = contract?.message?.name || null;
			const depositName = deposit?.message?.name || null;
			const canCreateContract =
				!contractName &&
				(!settings?.require_deposit_before_contract_creation || depositName);

			frm.add_custom_button(
				__("Sales Order / Deposit"),
				function () {
					showSalesDocumentModal(frm, "Sales Order", enableExtraRows);
				},
				__("Create")
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
					__("Create")
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
					__("Create")
				);
			}
		}
	}

	if (currentStatus === "" && settings?.enable_site_survey == 1) {
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
