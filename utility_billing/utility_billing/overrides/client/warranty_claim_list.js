// Extends ERPNext's list settings for Warranty Claim
(() => {
	const settings = frappe.listview_settings["Warranty Claim"] || {};
	const erpnext_onload = settings.onload;

	settings.onload = function (listview) {
		if (erpnext_onload) erpnext_onload(listview);

		// One unsaved reading for the meters of the selected claims; the server checks them
		listview.page.add_action_item(__("Create Meter Reading"), () => {
			const names = listview.get_checked_items(true);
			if (!names.length) {
				frappe.msgprint(__("Select at least one Warranty Claim."));
				return;
			}

			frappe.model.open_mapped_doc({
				method: "utility_billing.utility_billing.utils.request_link.make_meter_reading_from_claims",
				source_name: names,
			});
		});
	};

	frappe.listview_settings["Warranty Claim"] = settings;
})();
