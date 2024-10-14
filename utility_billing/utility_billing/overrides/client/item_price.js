frappe.ui.form.on("Item Price", {
	refresh: function (frm) {
		check_and_set_rate_zero(frm);
	},

	tariffs: function (frm) {
		check_and_set_rate_zero(frm);
	},
});

// Helper function to check tariff table and set rate to zero
function check_and_set_rate_zero(frm) {
	if (frm.doc.tariffs && frm.doc.tariffs.length > 0) {
		frm.set_value("price_list_rate", 0);
	}
}
