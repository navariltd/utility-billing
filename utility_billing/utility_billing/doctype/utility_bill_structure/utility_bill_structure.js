frappe.ui.form.on("Utility Bill Structure", {
	async refresh(frm) {
		calculate_overall_total(frm);

		const today = frappe.datetime.get_today();
		frappe.db
			.get_value(
				"Fiscal Year",
				{
					year_start_date: ["<=", today],
					year_end_date: [">=", today],
				},
				["name", "year_start_date", "year_end_date"]
			)
			.then((result) => {
				if (result && result.message) {
					frm.set_value("fiscal_year", result.message.name);
					frm.set_value("start_date", result.message.year_start_date);
					frm.set_value("end_date", result.message.year_end_date);
				}
			});

		if (!frm.doc.fiscal_year) {
			frm.set_value("fiscal_year", frappe.defaults.get_user_default("fiscal_year"));
		}

		frm.fields_dict["items"].grid.get_field("item").get_query = function () {
			return {
				filters: {
					is_sales_item: 1,
					is_utility_item: 1,
					has_variants: 0,
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
