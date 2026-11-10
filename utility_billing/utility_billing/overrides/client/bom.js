frappe.ui.form.on("BOM", {
	setup: function (frm) {
		// ERPNext sets its Item query in its own setup, which runs first. Keep it, because
		// the same form is reused for every BOM opened in this session.
		frm.erpnext_item_query = frm.fields_dict.item.get_query;
	},

	refresh: function (frm) {
		set_request_item_query(frm);
	},

	utility_service_request: function (frm) {
		set_request_item_query(frm);
	},
});

// A BOM made for a request is for one of the request's items. ERPNext's own query
// offers stock items only, which hides service items such as New Connection.
async function set_request_item_query(frm) {
	const request = frm.doc.utility_service_request;
	if (!request) {
		frm.fields_dict.item.get_query = frm.erpnext_item_query;
		frm.set_intro("");
		return;
	}

	if (frm.is_new() && frm.doc.is_default) {
		// The server unticks it on insert; show that before the first save.
		frm.set_value("is_default", 0);
	}

	const doc = await frappe.db.get_doc("Utility Service Request", request);
	const itemCodes = [...new Set((doc.items || []).map((row) => row.item_code).filter(Boolean))];

	frm.set_query("item", () => ({ filters: { name: ["in", itemCodes] } }));
	frm.set_intro(__("This BOM is for request {0}.", [request]), "blue");
}
