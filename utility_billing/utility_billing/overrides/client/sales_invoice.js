// Line helpers of the Sales Invoice item grid.
//
// A line whose revenue is deferred to a later date has to be billed at the rate
// valid on that date, and a rent line bills a property through the service item
// of that property: both are kept in step here.

// Rates already resolved per line (line, item and date), so a form refresh or a
// rate edited by hand does not resolve the same rate over and over. The var form
// keeps the cache when the script is evaluated again on the same page.
var resolved_line_rates = resolved_line_rates || {};

frappe.ui.form.on("Sales Invoice", {
	// The posting dates of the lines are filled on the server when the invoice is
	// saved, so their rates are brought in line with them when the form opens.
	refresh: function (frm) {
		(frm.doc.items || []).forEach((row) => {
			apply_rate_of_deferred_date(frm, row.doctype, row.name);
		});
	},
});

frappe.ui.form.on("Sales Invoice Item", {
	item_code: function (frm, cdt, cdn) {
		set_property_of_item(frm, cdt, cdn);
	},

	utility_property: function (frm, cdt, cdn) {
		set_item_of_property(frm, cdt, cdn);
	},

	custom_posting_date: function (frm, cdt, cdn) {
		apply_rate_of_deferred_date(frm, cdt, cdn, true);
	},

	// ERPNext applies the rate of the invoice posting date to these fields, so
	// both are used to correct the rate to the deferred posting date afterwards.
	price_list_rate: function (frm, cdt, cdn) {
		apply_rate_of_deferred_date(frm, cdt, cdn);
	},

	rate: function (frm, cdt, cdn) {
		apply_rate_of_deferred_date(frm, cdt, cdn);
	},
});

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
//
// The rate resolved for a line is remembered by line, item and date, so a form
// refresh or a rate edited by hand does not resolve it over and over.
function apply_rate_of_deferred_date(frm, cdt, cdn, force) {
	const row = locals[cdt][cdn];

	if (frm.doc.docstatus !== 0 || frm.doc.is_return) {
		return;
	}

	if (!row.item_code || !row.custom_posting_date) {
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
