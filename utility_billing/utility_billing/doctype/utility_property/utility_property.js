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

		render_gallery_preview(frm);
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
					fields: ["location", "asset_category", "net_purchase_amount"],
					limit_page_length: 1,
				},
				callback: function (r) {
					if (r.message?.length) {
						const asset = r.message[0];
						frm.set_value("location", asset.location);
						frm.set_value("asset_category", asset.asset_category);
						frm.set_value("net_purchase_amount", asset.net_purchase_amount);
					}
				},
			});
		}
	},
});

frappe.ui.form.on("Property Gallery Image", {
	image: render_gallery_preview,
	title: render_gallery_preview,
	category: render_gallery_preview,
	display_order: render_gallery_preview,
	image_gallery_remove: render_gallery_preview,
	form_render: render_gallery_preview,
});

function render_gallery_preview(frm) {
	const wrapper = frm.get_field("gallery_preview")?.$wrapper;

	if (!wrapper) return;

	const images = (frm.doc.image_gallery || [])
		.filter((row) => row.image)
		.sort((a, b) => (a.display_order || 0) - (b.display_order || 0));

	if (!images.length) {
		wrapper.html(`
			<div class="text-muted" style="padding:16px;text-align:center;">
				No gallery images added.
			</div>
		`);
		return;
	}

	wrapper.html(`
		<div style="
			display:grid;
			grid-template-columns:repeat(auto-fill,minmax(180px,1fr));
			gap:16px;
			padding-bottom:16px;
		">
			${images
				.map(
					(row) => `
					<div style="
						border:1px solid var(--border-color);
						border-radius:8px;
						overflow:hidden;
						background:#fff;
					">
						<img
							src="${row.image}"
							style="
								width:100%;
								height:160px;
								object-fit:cover;
								display:block;
							"
						/>
						<div style="padding:10px;">
							<div style="font-weight:600;">
								${frappe.utils.escape_html(row.title || "Untitled")}
							</div>
							${
								row.category
									? `<div class="text-muted" style="margin-top:4px;">${frappe.utils.escape_html(row.category)}</div>`
									: ""
							}
						</div>
					</div>
				`,
				)
				.join("")}
		</div>
	`);
}
