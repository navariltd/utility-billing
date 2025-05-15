frappe.ui.form.on("Utility Bill Structure", {
	refresh(frm) {
		calculate_overall_total(frm);
	},

	items_on_form_rendered(frm) {
		frm.fields_dict.items.grid.wrapper.on("change", () => {
			calculate_overall_total(frm);
		});
	},

	fiscal_year(frm) {
		if (frm.doc.fiscal_year) {
			frappe.db
				.get_value("Fiscal Year", frm.doc.fiscal_year, [
					"year_start_date",
					"year_end_date",
				])
				.then((r) => {
					if (r.message) {
						frm.set_value("start_date", r.message.year_start_date);
						frm.set_value("end_date", r.message.year_end_date);
					}
				});
		}
	},
});

frappe.ui.form.on("Utility Bill Structure Item", {
	amount(frm, cdt, cdn) {
		calculate_row_total(frm, cdt, cdn);
		calculate_overall_total(frm);
	},
	discount(frm, cdt, cdn) {
		calculate_row_total(frm, cdt, cdn);
		calculate_overall_total(frm);
	},
});

function calculate_row_total(frm, cdt, cdn) {
	let row = locals[cdt][cdn];
	let amount = parseFloat(row.amount) || 0;
	let discount = parseFloat(row.discount) || 0;

	let total = amount - (discount / 100) * amount;
	frappe.model.set_value(cdt, cdn, "total", total);
}

function calculate_overall_total(frm) {
	let total = 0;
	(frm.doc.items || []).forEach((row) => {
		total += parseFloat(row.total) || 0;
	});
	frm.set_value("total_amount", total);
}
