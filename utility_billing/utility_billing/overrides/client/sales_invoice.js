// Line helpers of the Sales Invoice item grid.
//
// A line whose revenue is deferred to a later date has to be billed at the rate
// valid on that date, and a rent line bills a property through the service item
// of that property: both are kept in step here.
//
// Under the Item Price billing approach, utility lines (items flagged
// `is_utility_item`) are also governed by a Utility Service Request, carried by
// each line: the request leasing the line's property on its date, or for an
// item without a property the one request without properties covering the
// date. Where several qualify the user picks one on the line. The rates follow
// the line's request - primary lines the Item Price valid on their date,
// secondary lines the rate on the request row. A rate typed by hand is put back
// when the field is left. The header request stays read only; only a draft Auto
// Repeat generated from an invoice linked through its header keeps using it. The
// server enforces all of this again on save; this is UX only.

// Rates already resolved per line (line, item and date), so a form refresh or a
// rate edited by hand does not resolve the same rate over and over. The var form
// keeps the cache when the script is evaluated again on the same page.
var resolved_line_rates = resolved_line_rates || {};

var UTILITY_API = "utility_billing.api.sales_invoice";

frappe.ui.form.on("Sales Invoice", {
	setup: function (frm) {
		set_line_request_query(frm);
	},

	// The posting dates of the lines are filled on the server when the invoice is
	// saved, so their rates are brought in line with them when the form opens.
	refresh: function (frm) {
		(frm.doc.items || []).forEach((row) => {
			apply_rate_of_deferred_date(frm, row.doctype, row.name);
		});

		govern_utility_lines(frm);
	},

	customer: function (frm) {
		govern_utility_lines(frm);
	},

	// Editable only on a draft that keeps its header request (see above).
	utility_service_request: function (frm) {
		govern_utility_lines(frm);
	},
});

frappe.ui.form.on("Sales Invoice Item", {
	item_code: function (frm, cdt, cdn) {
		set_property_of_item(frm, cdt, cdn);
		govern_utility_lines(frm, cdn);
	},

	// ERPNext copies the first row's accounting dimensions, the property included,
	// into a new row. Remember what it copied, so a service line is not left on a
	// property the user never picked.
	items_add: function (frm, cdt, cdn) {
		setTimeout(() => {
			const row = locals[cdt] && locals[cdt][cdn];
			if (row && row.utility_property) row.__copied_property = row.utility_property;
		}, 0);
	},

	utility_property: function (frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (row.__copied_property && row.utility_property !== row.__copied_property) {
			delete row.__copied_property; // picked by the user
		}
		set_item_of_property(frm, cdt, cdn);
		set_cost_center_of_property(frm, cdt, cdn);
		govern_utility_lines(frm, cdn);
	},

	cost_center: function (frm, cdt, cdn) {
		set_property_of_cost_center(frm, cdt, cdn);
	},

	utility_service_request: function (frm, cdt, cdn) {
		govern_utility_lines(frm, cdn);
	},

	items_remove: function (frm) {
		govern_utility_lines(frm);
	},

	custom_posting_date: function (frm, cdt, cdn) {
		// The date may give the line another request
		govern_utility_lines(frm, cdn);
		if (enforce_governed_rate(frm, cdt, cdn)) return;
		apply_rate_of_deferred_date(frm, cdt, cdn, true);
	},

	// ERPNext applies the rate of the invoice posting date to these fields, so
	// both are used to correct the rate to the deferred posting date afterwards.
	price_list_rate: function (frm, cdt, cdn) {
		if (revert_governed_rate(frm, cdt, cdn, "price_list_rate")) return;
		apply_rate_of_deferred_date(frm, cdt, cdn);
	},

	rate: function (frm, cdt, cdn) {
		if (revert_governed_rate(frm, cdt, cdn, "rate")) return;
		apply_rate_of_deferred_date(frm, cdt, cdn);
	},
});

// Resolve whether rent is billed by Item Price; governance applies only then.
function is_item_price_approach() {
	return frappe.db
		.get_single_value("Utility Billing Settings", "rent_billing_approach")
		.then((approach) => approach === "Item Price");
}

// A line's request is picked among the requests the server found for that
// line: the one it resolved to, or the several the user chooses between. The
// field stays visible and editable, since Frappe hides an empty read only
// field; a request the line cannot have is replaced when the lines are resolved
// again, and on save.
function set_line_request_query(frm) {
	frm.set_query("utility_service_request", "items", (doc, cdt, cdn) => {
		const filters = { docstatus: 1 };
		const entry = (frm.utility_line_results || {})[cdn];

		if (frm.doc.customer) {
			filters.customer = frm.doc.customer;
		}
		if (entry) {
			filters.name = ["in", (entry.candidates || []).length ? entry.candidates : [""]];
		}

		return { filters };
	});
}

// Find the request of each utility line once a utility item and the customer
// are set - whichever comes first.
function govern_utility_lines(frm, cdn) {
	if (frm.doc.docstatus !== 0 || frm.doc.is_return) {
		return;
	}

	// The request's own rows are still being added from the Utility Service
	// Request, which catches the invoice up once they are all in.
	if (frappe.flags.filling_rows_from_service_request) {
		return;
	}

	const has_item = (frm.doc.items || []).some((row) => row.item_code && !row.meter_reading);

	if (!frm.doc.customer || !has_item) {
		frm.utility_line_results = {};
		return;
	}

	const sequence = (frm.utility_match_sequence = (frm.utility_match_sequence || 0) + 1);

	is_item_price_approach().then((applies) => {
		toggle_header_request(frm, applies);
		if (!applies) return;

		frappe.call({
			method: `${UTILITY_API}.resolve_invoice_lines`,
			args: { doc: frm.doc },
			callback: function (r) {
				if (sequence !== frm.utility_match_sequence) return; // superseded

				// Picking an item makes ERPNext send the invoice to the server
				// (process_item_selection) and sync the server copy back when it
				// answers, deleting any field set on the form in between. Acting
				// once no request is in flight keeps the requests and rates in place.
				frappe.after_ajax(() => {
					if (sequence !== frm.utility_match_sequence) return; // superseded meanwhile

					handle_line_resolutions(frm, r.message || {}, cdn);
				});
			},
		});
	});
}

// Under Item Price the header request is read only, except on a draft that
// keeps it (see above).
function toggle_header_request(frm, item_price) {
	const keeps_header = !!(frm.doc.auto_repeat && frm.doc.utility_service_request);
	frm.set_df_property("utility_service_request", "read_only", item_price && !keeps_header ? 1 : 0);
}

// Fill each line's request and property, let the user pick a request where
// several qualify, and say why a line has none.
function handle_line_resolutions(frm, result, cdn) {
	frm.utility_line_results = result.applies ? result.rows || {} : {};
	frm.utility_header_path = !!result.header_path;

	if (!result.applies) return;

	// A service line still on the property ERPNext copied from the first row is
	// cleared, so the user picks its property; then the lines are found again.
	const copied = (frm.doc.items || []).filter((row) => {
		const entry = frm.utility_line_results[row.name];
		return (
			!result.header_path &&
			entry &&
			!entry.rent_item &&
			row.__copied_property &&
			row.utility_property === row.__copied_property
		);
	});
	if (copied.length) {
		copied.forEach((row) => {
			row.utility_property = null;
			delete row.__copied_property;
		});
		govern_utility_lines(frm);
		return;
	}

	const messages = [];
	const updates = [];

	(frm.doc.items || []).forEach((row) => {
		const entry = frm.utility_line_results[row.name];

		if (!entry) return;

		if (entry.status === "not_listed" && row.name === cdn) {
			block_utility_line(frm, entry, cdn);
			return;
		}

		if (!result.header_path) {
			const request = entry.service_request || (entry.editable ? row.utility_service_request : null);
			if ((row.utility_service_request || null) !== (request || null)) {
				updates.push([row, "utility_service_request", request || null]);
			}
			if (entry.utility_property && !row.utility_property) {
				updates.push([row, "utility_property", entry.utility_property]);
			}
		}

		if (entry.message) messages.push(entry.message);
	});

	updates.forEach(([row, fieldname, value]) => {
		row[fieldname] = value; // set directly: set_value would resolve the lines again
	});

	frm.refresh_field("items");

	(frm.doc.items || []).forEach((row) => {
		if (get_governed_line(frm, row)) enforce_governed_rate(frm, row.doctype, row.name);
	});

	if (messages.length) {
		frappe.show_alert({ message: messages.join("<br>"), indicator: "orange" }, 10);
	}
}

// Remove the line just added that cannot be billed: its item is on no request
// of the customer.
function block_utility_line(frm, entry, cdn) {
	frappe.msgprint({
		title: __("Utility item not allowed"),
		message: entry.message,
		indicator: "red",
	});

	const grid_row = frm.fields_dict.items.grid.get_row(cdn);
	if (grid_row) grid_row.remove();
}

// The resolved request line billed by a row, if any.
function get_governed_line(frm, row) {
	if (!row || !row.item_code || row.meter_reading) return null;
	if (frm.doc.docstatus !== 0 || frm.doc.is_return) return null;

	const entry = (frm.utility_line_results || {})[row.name];

	return entry && entry.status === "resolved" && entry.role ? entry : null;
}

// Set the rate of a governed row. Returns whether the row is governed.
//
// A rent line takes its request's Item Price as its price list rate, and ERPNext
// derives its rate from it. A service line is prefilled with its
// request row's rate while the user has not changed it, and stays editable.
// A draft keeping its header request is held to both rates, as before.
function enforce_governed_rate(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	const line = get_governed_line(frm, row);

	if (!line) return false;

	if (line.role === "secondary") {
		if (frm.utility_header_path) {
			set_governed_rate(frm, row, flt(line.rate));
		} else if (!flt(row.rate) || flt(row.rate) === flt(row.__prefilled_rate)) {
			row.__prefilled_rate = flt(line.rate);
			frappe.model.set_value(row.doctype, row.name, { price_list_rate: flt(line.rate), rate: flt(line.rate) });
		}
		return true;
	}

	const item_code = row.item_code;

	frappe.call({
		method: `${UTILITY_API}.get_line_rate`,
		args: {
			item_code: item_code,
			posting_date: row.custom_posting_date || frm.doc.posting_date,
			customer: frm.doc.customer,
			utility_service_request: line.service_request,
			price_list: frm.doc.selling_price_list,
			uom: row.uom,
			qty: row.qty,
			conversion_factor: row.conversion_factor,
			plc_conversion_rate: frm.doc.plc_conversion_rate,
			conversion_rate: frm.doc.conversion_rate,
		},
		callback: function (r) {
			// A missing Item Price is reported by the server on save.
			if (r.message === null || r.message === undefined) return;
			if (!locals[cdt][cdn] || locals[cdt][cdn].item_code !== item_code) return;

			if (frm.utility_header_path) {
				set_governed_rate(frm, locals[cdt][cdn], flt(r.message));
			} else {
				set_governed_price(frm, locals[cdt][cdn], flt(r.message));
			}
		},
	});

	return true;
}

function set_governed_rate(frm, row, rate) {
	frm.utility_expected_rates = frm.utility_expected_rates || {};
	frm.utility_expected_rates[row.name] = rate;

	const values = {};

	if (flt(row.price_list_rate) !== rate) values.price_list_rate = rate;
	if (flt(row.rate) !== rate) values.rate = rate;

	if (Object.keys(values).length) {
		frappe.model.set_value(row.doctype, row.name, values);
	}
}

// Set only the price list rate of a rent line; ERPNext derives the rate from it.
function set_governed_price(frm, row, rate) {
	frm.utility_expected_prices = frm.utility_expected_prices || {};
	frm.utility_expected_prices[row.name] = rate;

	if (flt(row.price_list_rate) !== rate) {
		frappe.model.set_value(row.doctype, row.name, "price_list_rate", rate);
	}
}

// Put back a governed rate edited by hand. Returns whether the row is governed.
//
// A service line's rate is the user's. A rent line's price list rate is put
// back; its rate is left to ERPNext. A draft keeping its header request is held
// to both, as before.
function revert_governed_rate(frm, cdt, cdn, fieldname) {
	const row = locals[cdt][cdn];
	const line = get_governed_line(frm, row);

	if (!line) return false;

	if (!frm.utility_header_path) {
		if (line.role === "secondary" || fieldname !== "price_list_rate") return true;

		const price = (frm.utility_expected_prices || {})[cdn];
		if (price === undefined || flt(row.price_list_rate) === flt(price)) return true;

		frappe.model.set_value(cdt, cdn, "price_list_rate", price);
		frappe.show_alert({
			message: __("The price list rate of {0} is the Item Price of Utility Service Request {1}.", [
				row.item_code,
				line.service_request,
			]),
			indicator: "orange",
		});
		return true;
	}

	const expected = (frm.utility_expected_rates || {})[cdn];

	if (expected === undefined) return true; // still resolving

	if (flt(row[fieldname], precision(fieldname, row)) === flt(expected, precision(fieldname, row))) {
		return true;
	}

	frappe.model.set_value(cdt, cdn, fieldname, expected);
	frappe.show_alert({
		message: __("The rate of {0} is set by Utility Service Request {1} and cannot be changed.", [
			row.item_code,
			line.service_request,
		]),
		indicator: "orange",
	});

	return true;
}

// Fill the cost center of a line from its property, unless one was set by hand
// (anything but blank, the company default, or the one filled from a property).
function set_cost_center_of_property(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	if (frm.doc.docstatus !== 0 || !row.utility_property) return;

	Promise.all([
		frappe.db.get_value("Utility Property", row.utility_property, "cost_center"),
		frappe.db.get_value("Company", frm.doc.company, "cost_center"),
	]).then(([property, company]) => {
		const cost_center = property.message && property.message.cost_center;
		const company_default = company.message && company.message.cost_center;
		const current = locals[cdt][cdn];
		if (!cost_center || !current || current.utility_property !== row.utility_property) return;

		if (!current.cost_center || current.cost_center === company_default || current.cost_center === current.__filled_cost_center) {
			current.__filled_cost_center = cost_center;
			frappe.model.set_value(cdt, cdn, "cost_center", cost_center);
		}
	});
}

// Fill the property of a utility line from its cost center, when exactly one
// property uses that cost center.
function set_property_of_cost_center(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	const entry = (frm.utility_line_results || {})[cdn];
	if (frm.doc.docstatus !== 0 || !row.cost_center || row.utility_property || !entry || entry.rent_item) return;
	if (row.cost_center === row.__filled_cost_center) return;

	frappe.call({
		method: `${UTILITY_API}.get_property_of_cost_center`,
		args: { cost_center: row.cost_center },
		callback: function (r) {
			const current = locals[cdt][cdn];
			if (r.message && current && !current.utility_property) {
				frappe.model.set_value(cdt, cdn, "utility_property", r.message);
			}
		},
	});
}

// Fill the property billed by the selected item, when the item is the service
// item of a property.
function set_property_of_item(frm, cdt, cdn) {
	const row = locals[cdt][cdn];

	if (frm.doc.docstatus !== 0 || !row.item_code) {
		return;
	}

	frappe.call({
		method: "utility_billing.api.sales_invoice.get_line_utility_property",
		args: { item_code: row.item_code },
		callback: function (r) {
			const property = r.message;

			if (property && property !== row.utility_property) {
				frappe.model.set_value(cdt, cdn, "utility_property", property);
			}
		},
	});
}

// Fill the service item of the selected property, when the line has no item yet.
function set_item_of_property(frm, cdt, cdn) {
	const row = locals[cdt][cdn];

	if (frm.doc.docstatus !== 0 || !row.utility_property || row.item_code) {
		return;
	}

	frappe.call({
		method: "utility_billing.api.sales_invoice.get_line_item",
		args: { utility_property: row.utility_property },
		callback: function (r) {
			if (r.message) {
				frappe.model.set_value(cdt, cdn, "item_code", r.message);
			}
		},
	});
}

// Replace the rate of the line by the rate valid on its Deferred Posting Date.
// Governed utility lines are kept in step by their request instead.
//
// The rate resolved for a line is remembered by line, item and date, so a form
// refresh or a rate edited by hand does not resolve it over and over.
function apply_rate_of_deferred_date(frm, cdt, cdn, force) {
	const row = locals[cdt][cdn];

	if (frm.doc.docstatus !== 0 || frm.doc.is_return) {
		return;
	}

	if (!row.item_code || !row.custom_posting_date || get_governed_line(frm, row)) {
		return;
	}

	if (row.custom_posting_date === frm.doc.posting_date) {
		return; // the rate of the invoice posting date is already applied
	}

	const key = `${row.name}|${row.item_code}|${row.custom_posting_date}`;

	if (!force && resolved_line_rates[key] === flt(row.price_list_rate)) {
		return; // the rate of the deferred posting date is already applied
	}

	frappe.call({
		method: "utility_billing.api.sales_invoice.get_line_rate",
		args: {
			item_code: row.item_code,
			posting_date: row.custom_posting_date,
			customer: frm.doc.customer,
			utility_service_request: row.utility_service_request || frm.doc.utility_service_request,
			price_list: frm.doc.selling_price_list,
			uom: row.uom,
			qty: row.qty,
			conversion_factor: row.conversion_factor,
			plc_conversion_rate: frm.doc.plc_conversion_rate,
			conversion_rate: frm.doc.conversion_rate,
		},
		callback: function (r) {
			const rate = r.message;

			if (rate === null || rate === undefined) {
				return;
			}

			resolved_line_rates[key] = flt(rate);

			if (flt(row.price_list_rate) !== flt(rate)) {
				// ERPNext derives the rate and the totals from the price list rate.
				frappe.model.set_value(cdt, cdn, "price_list_rate", rate);
			}
		},
	});
}