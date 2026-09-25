// Line helpers of the Sales Invoice item grid.
//
// A line whose revenue is deferred to a later date has to be billed at the rate
// valid on that date, and a rent line bills a property through the service item
// of that property: both are kept in step here.
//
// Under the Item Price billing approach, utility lines (items flagged
// `is_utility_item`) are also governed by a Utility Service Request: the invoice
// is linked to the one request of the customer covering all of them, that
// request's utility items are pre-filled, and their rates follow the request -
// primary lines the Item Price valid on their date, secondary lines the rate on
// the request row. A rate typed by hand is put back when the field is left. The
// server enforces all of this again on save; this is UX only.

// Rates already resolved per line (line, item and date), so a form refresh or a
// rate edited by hand does not resolve the same rate over and over. The var form
// keeps the cache when the script is evaluated again on the same page.
var resolved_line_rates = resolved_line_rates || {};

var UTILITY_API = "utility_billing.api.sales_invoice";

frappe.ui.form.on("Sales Invoice", {
	setup: function (frm) {
		set_service_request_query(frm);
	},

	// The posting dates of the lines are filled on the server when the invoice is
	// saved, so their rates are brought in line with them when the form opens.
	refresh: function (frm) {
		(frm.doc.items || []).forEach((row) => {
			apply_rate_of_deferred_date(frm, row.doctype, row.name);
		});

		load_service_request_lines(frm, false);
	},

	customer: function (frm) {
		govern_utility_lines(frm);
	},

	utility_service_request: function (frm) {
		load_service_request_lines(frm, true);
	},
});

frappe.ui.form.on("Sales Invoice Item", {
	item_code: function (frm, cdt, cdn) {
		set_property_of_item(frm, cdt, cdn);
		govern_utility_lines(frm, cdn);
	},

	utility_property: function (frm, cdt, cdn) {
		set_item_of_property(frm, cdt, cdn);
	},

	items_remove: function (frm) {
		govern_utility_lines(frm);
	},

	custom_posting_date: function (frm, cdt, cdn) {
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

// Only submitted requests of the customer can be linked, narrowed to the
// requests covering every utility line once they are known.
function set_service_request_query(frm) {
	frm.set_query("utility_service_request", () => {
		const filters = { docstatus: 1 };

		if (frm.doc.customer) {
			filters.customer = frm.doc.customer;
		}
		if ((frm.utility_request_candidates || []).length) {
			filters.name = ["in", frm.utility_request_candidates];
		}

		return { filters };
	});
}

// Match the utility lines of the invoice to the customer's requests, once both
// a utility item and the customer are set - whichever comes first.
function govern_utility_lines(frm, cdn) {
	if (frm.doc.docstatus !== 0 || frm.doc.is_return || frm.prefilling_utility_lines) {
		return;
	}

	const item_codes = [
		...new Set(
			(frm.doc.items || [])
				.filter((row) => row.item_code && !row.meter_reading)
				.map((row) => row.item_code),
		),
	];

	if (!frm.doc.customer || !item_codes.length) {
		frm.utility_request_candidates = [];
		clear_orphaned_service_request(frm);
		return;
	}

	const new_row = cdn ? locals["Sales Invoice Item"][cdn] : null;
	const sequence = (frm.utility_match_sequence = (frm.utility_match_sequence || 0) + 1);

	is_item_price_approach().then((applies) => {
		if (!applies) return;

		frappe.call({
			method: `${UTILITY_API}.match_utility_service_requests`,
			args: {
				customer: frm.doc.customer,
				item_codes: item_codes,
				new_item_code: new_row ? new_row.item_code : null,
			},
			callback: function (r) {
				if (sequence !== frm.utility_match_sequence) return; // superseded

				// Picking an item makes ERPNext send the invoice to the server
				// (process_item_selection) and sync the server copy back when it
				// answers, deleting any field set on the form in between. Acting
				// once no request is in flight keeps the link and rates in place.
				frappe.after_ajax(() => {
					if (sequence !== frm.utility_match_sequence) return; // superseded meanwhile

					handle_request_match(frm, r.message || {}, cdn);
				});
			},
		});
	});
}

// Clear a linked request once the invoice no longer bills any of its utility
// items - an invoice with no utility item has nothing left to govern.
function clear_orphaned_service_request(frm) {
	if (frm.doc.utility_service_request) {
		frm.set_value("utility_service_request", null);
	}
}

function handle_request_match(frm, match, cdn) {
	frm.utility_request_candidates = match.applies ? match.candidates || [] : [];

	if (!match.applies) {
		clear_orphaned_service_request(frm);
		return;
	}

	if (!match.status) {
		// No utility item on the invoice at all.
		clear_orphaned_service_request(frm);
		return;
	}

	if (match.status === "missing" || match.status === "conflict") {
		block_utility_line(frm, match, cdn);
		return;
	}

	const linked = frm.doc.utility_service_request;

	if (linked && match.candidates.includes(linked)) {
		if (cdn) enforce_governed_rate(frm, "Sales Invoice Item", cdn);
		return;
	}

	if (match.status === "single") {
		frm.set_value("utility_service_request", match.candidates[0]);
		return;
	}

	// Several requests qualify: the user picks one, the picker lists only them.
	if (linked) {
		frm.set_value("utility_service_request", null);
	}

	frappe.show_alert(
		{
			message: __(
				"Several Utility Service Requests of {0} cover the utility items on this invoice. Select one in the Utility Service Request field.",
				[frm.doc.customer],
			),
			indicator: "orange",
		},
		10,
	);
	frm.scroll_to_field("utility_service_request");
}

// Remove the line that cannot be billed. When the customer changed instead, the
// lines stay for the user to fix and the request is unlinked.
function block_utility_line(frm, match, cdn) {
	frappe.msgprint({
		title: __("Utility item not allowed"),
		message: match.message,
		indicator: "red",
	});

	const row = cdn ? locals["Sales Invoice Item"][cdn] : null;
	const is_culprit =
		row && (match.status === "conflict" || (match.missing || []).includes(row.item_code));
	const grid_row = is_culprit ? frm.fields_dict.items.grid.get_row(cdn) : null;

	if (grid_row) {
		grid_row.remove();
		return;
	}

	if (frm.doc.utility_service_request) {
		frm.set_value("utility_service_request", null);
	}
}

// Load the governed lines of the linked request and bring every line in step.
// When the request was just linked its utility items are pre-filled first.
function load_service_request_lines(frm, prefill) {
	frm.utility_lines = {};
	frm.utility_expected_rates = {};

	const request = frm.doc.utility_service_request;

	if (frm.doc.docstatus !== 0 || frm.doc.is_return || !request) {
		return;
	}

	is_item_price_approach().then((applies) => {
		if (!applies) return;

		frappe.call({
			method: `${UTILITY_API}.get_utility_service_request_lines`,
			args: { utility_service_request: request },
			callback: function (r) {
				if (frm.doc.utility_service_request !== request) return; // relinked meanwhile

				const lines = r.message || [];
				lines.forEach((line) => {
					frm.utility_lines[line.item_code] = line;
				});

				const ready = prefill ? prefill_service_request_lines(frm, lines) : Promise.resolve();

				// Pre-filled items are still being processed by ERPNext; their
				// answers would overwrite the rates if these were set first.
				ready
					.then(() => frappe.after_ajax())
					.then(() => {
						if (frm.doc.utility_service_request !== request) return; // relinked meanwhile

						(frm.doc.items || []).forEach((row) => {
							enforce_governed_rate(frm, row.doctype, row.name);
						});
					});
			},
		});
	});
}

// Add the request's utility items the invoice does not bill yet.
async function prefill_service_request_lines(frm, lines) {
	const billed = new Set((frm.doc.items || []).map((row) => row.item_code));
	const missing = lines.filter((line) => !billed.has(line.item_code));

	if (!missing.length) return;

	frm.prefilling_utility_lines = true;

	try {
		for (const line of missing) {
			const row = (frm.doc.items || []).find((item) => !item.item_code) || frm.add_child("items");

			await frappe.model.set_value(row.doctype, row.name, "item_code", line.item_code);
			await frappe.model.set_value(row.doctype, row.name, "qty", line.qty);
		}
	} finally {
		frm.prefilling_utility_lines = false;
	}

	frm.refresh_field("items");
}

// The governed line of the linked request billed by a row, if any.
function get_governed_line(frm, row) {
	if (!row || !row.item_code || row.meter_reading) return null;
	if (frm.doc.docstatus !== 0 || frm.doc.is_return) return null;

	return (frm.utility_lines || {})[row.item_code] || null;
}

// Set the rate a governed row must bill. Returns whether the row is governed.
function enforce_governed_rate(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	const line = get_governed_line(frm, row);

	if (!line) return false;

	if (line.role === "secondary") {
		set_governed_rate(frm, row, flt(line.rate));
		return true;
	}

	frappe.call({
		method: `${UTILITY_API}.get_line_rate`,
		args: {
			item_code: row.item_code,
			posting_date: row.custom_posting_date || frm.doc.posting_date,
			customer: frm.doc.customer,
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
			if (!locals[cdt][cdn] || locals[cdt][cdn].item_code !== line.item_code) return;

			set_governed_rate(frm, locals[cdt][cdn], flt(r.message));
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

// Put back a governed rate edited by hand. Returns whether the row is governed.
function revert_governed_rate(frm, cdt, cdn, fieldname) {
	const row = locals[cdt][cdn];

	if (!get_governed_line(frm, row)) return false;

	const expected = (frm.utility_expected_rates || {})[cdn];

	if (expected === undefined) return true; // still resolving

	if (flt(row[fieldname], precision(fieldname, row)) === flt(expected, precision(fieldname, row))) {
		return true;
	}

	frappe.model.set_value(cdt, cdn, fieldname, expected);
	frappe.show_alert({
		message: __("The rate of {0} is set by Utility Service Request {1} and cannot be changed.", [
			row.item_code,
			frm.doc.utility_service_request,
		]),
		indicator: "orange",
	});

	return true;
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