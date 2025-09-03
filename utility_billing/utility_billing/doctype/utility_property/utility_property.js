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

		// Manage field states based on existing asset selection
		this.manage_asset_fields(frm);

		// Add button to view asset details
		if (frm.doc.existing_asset && frm.doc.is_existing_asset) {
			frm.add_custom_button(__("View Asset Details"), function() {
				frm.call({
					method: "update_asset_from_property",
					doc: frm.doc,
					callback: function(response) {
						if (response.message && !response.message.error) {
							const result = response.message;
							const asset_status = result.asset_status === "submitted" ? " (Submitted Asset)" : " (Draft Asset)";
							
							// Show asset information in a dialog
							let message = "Using existing asset information" + asset_status;
							if (result.asset_data) {
								message += "<br><br><strong>Asset Details:</strong><br>";
								message += `Asset Name: ${result.asset_data.asset_name || 'Not set'}<br>`;
								message += `Location: ${result.asset_data.location || 'Not set'}<br>`;
								message += `Category: ${result.asset_data.asset_category || 'Not set'}<br>`;
								message += `Purchase Amount: ${result.asset_data.gross_purchase_amount || 'Not set'}<br>`;
								message += `Purchase Date: ${result.asset_data.purchase_date || 'Not set'}<br>`;
								message += `Item Code: ${result.asset_data.item_code || 'Not set'}<br>`;
								message += `Company: ${result.asset_data.company || 'Not set'}<br>`;
								message += `Owner: ${result.asset_data.asset_owner || 'Not set'}<br>`;
								message += `Custodian: ${result.asset_data.custodian || 'Not set'}<br>`;
								message += `Status: ${result.asset_data.status || 'Not set'}`;
							}
							if (result.note) {
								message += "<br><br><em>" + result.note + "</em>";
							}
							
							frappe.msgprint({
								title: __("Asset Information"),
								message: message,
								indicator: "blue"
							});
						} else if (response.message && response.message.error) {
							frappe.msgprint({
								title: __("Error"),
								message: response.message.error,
								indicator: "red"
							});
						}
					},
					error: function(response) {
						frappe.msgprint({
							title: __("Error"),
							message: __("Failed to fetch asset information."),
							indicator: "red"
						});
					}
				});
			}, __("Asset Actions"));
		}
	},

	is_existing_asset(frm) {
		// Clear existing asset field when unchecked
		if (!frm.doc.is_existing_asset) {
			frm.set_value("existing_asset", "");
		}
		// Manage field states
		frm.events.manage_asset_fields(frm);
	},

	item(frm) {
		// Only allow item selection if not using existing asset
		if (!frm.doc.is_existing_asset && frm.doc.item) {
			frappe.call({
				method: "frappe.client.get_list",
				args: {
					doctype: "Asset",
					filters: {
						item_code: frm.doc.item,
					},
					fields: ["location", "asset_category", "gross_purchase_amount"],
					limit_page_length: 1,
				},
				callback: function (r) {
					if (r.message && r.message.length > 0) {
						const asset = r.message[0];
						frm.set_value("location", asset.location);
						frm.set_value("asset_category", asset.asset_category);
						frm.set_value("gross_purchase_amount", asset.gross_purchase_amount);
					}
				},
			});
		}
	},

	existing_asset(frm) {
		if (frm.doc.existing_asset) {
			frappe.call({
				method: "frappe.client.get",
				args: {
					doctype: "Asset",
					name: frm.doc.existing_asset
				},
				callback: function(r) {
					if (r.message) {
						const asset = r.message;
						// Populate property fields with asset data (for display)
						frm.set_value("location", asset.location);
						frm.set_value("asset_category", asset.asset_category);
						frm.set_value("gross_purchase_amount", asset.gross_purchase_amount);
						frm.set_value("purchase_date", asset.purchase_date);
						
						// Also set the item field from the asset
						if (asset.item_code) {
							frm.set_value("item", asset.item_code);
						}

						// Show asset information without updating
						frappe.msgprint({
							title: __("Asset Selected"),
							message: __("Existing asset information is now being used for this property. Asset-related fields are now read-only."),
							indicator: "blue"
						});
						
						// Manage field states
						frm.events.manage_asset_fields(frm);
					}
				}
			});
		} else {
			// Re-enable fields when no existing asset is selected
			frm.events.manage_asset_fields(frm);
		}
	},

	manage_asset_fields(frm) {
		// Disable asset-related fields when existing asset is selected
		const disable_fields = frm.doc.is_existing_asset && frm.doc.existing_asset;
		
		frm.set_df_property("location", "read_only", disable_fields);
		frm.set_df_property("asset_category", "read_only", disable_fields);
		frm.set_df_property("gross_purchase_amount", "read_only", disable_fields);
		frm.set_df_property("purchase_date", "read_only", disable_fields);
		frm.set_df_property("item", "read_only", disable_fields);
		frm.set_df_property("asset_naming_series", "read_only", disable_fields);
		
		// Show/hide description based on field state
		if (disable_fields) {
			frm.set_df_property("location", "description", "Field is read-only when using existing asset");
			frm.set_df_property("asset_category", "description", "Field is read-only when using existing asset");
			frm.set_df_property("gross_purchase_amount", "description", "Field is read-only when using existing asset");
			frm.set_df_property("purchase_date", "description", "Field is read-only when using existing asset");
			frm.set_df_property("item", "description", "Field is read-only when using existing asset");
		} else {
			frm.set_df_property("location", "description", "");
			frm.set_df_property("asset_category", "description", "");
			frm.set_df_property("gross_purchase_amount", "description", "");
			frm.set_df_property("purchase_date", "description", "");
			frm.set_df_property("item", "description", "");
		}
	}
});
