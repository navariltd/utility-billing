frappe.ui.form.on("Item Price", {
	refresh: function (frm) {
		check_and_set_rate_zero(frm);
	},

	custom_item_price_tariffs: function (frm) {
		check_and_set_rate_zero(frm);
	},
});

// Helper function to check tariff table and set rate to zero
function check_and_set_rate_zero(frm) {
	if (frm.doc.custom_item_price_tariffs && frm.doc.custom_item_price_tariffs.length > 0) {
		frm.set_value("price_list_rate", 0);
	}
}
