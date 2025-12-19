// Copyright (c) 2024, Navari and contributors
// For license information, please see license.txt

frappe.ui.form.on("Utility Property", {
	refresh(frm) {
		frm.toggle_display("address_html", !frm.is_new());
		frm.toggle_display("contact_html", !frm.is_new());
		if (!frm.is_new()) {
			frappe.contacts.render_address_and_contact(frm);
		}
		frm.set_query("parent_utility_property", function () {
			return {
				filters: {
					is_group: 1,
				},
			};
		});
	},

	item(frm) {
		if (frm.doc.item) {
			frappe.call({
				method: "frappe.client.get_list",
				args: {
					doctype: "Asset",
					filters: {
						item_code: frm.doc.item,
					},
					fields: [
						"location",
						"asset_category",
						"gross_purchase_amount",
					],
					limit_page_length: 1,
				},
				callback: function (r) {
					if (r.message && r.message.length > 0) {
						const asset = r.message[0];
						frm.set_value("location", asset.location);
						frm.set_value("asset_category", asset.asset_category);
						frm.set_value(
							"gross_purchase_amount",
							asset.gross_purchase_amount,
						);
					}
				},
			});
		}
	},
});
