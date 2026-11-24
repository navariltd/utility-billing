frappe.ui.form.on("BOM", {
	setup: function (frm) {
		// ERPNext sets its Item query in its own setup, which runs first: stock items only,
		// unless Is Phantom BOM is ticked.
		const erpnext_item_query = frm.fields_dict.item.get_query;

		// Decided for each BOM when the query is read, because the same form is reused for
		// every BOM opened in this session. It has to be ready at once: Frappe validates an
		// Item prefilled by frappe.new_doc against this query right after the first render,
		// and clears a value the query does not return.
		frm.set_query("item", (doc, cdt, cdn) => {
			if (!doc.utility_service_request) {
				return erpnext_item_query ? erpnext_item_query(doc, cdt, cdn) : {};
			}

			// A BOM made for a request is for one of the request's items, service items
			// included. Until they are loaded, no filter: never ERPNext's stock only list.
			const loaded = frm.request_items;
			return loaded && loaded.request === doc.utility_service_request
				? { filters: { name: ["in", loaded.item_codes] } }
				: {};
		});
	},

	refresh: function (frm) {
		show_request_link(frm);
	},

	utility_service_request: function (frm) {
		show_request_link(frm);
	},
});

async function show_request_link(frm) {
	const request = frm.doc.utility_service_request;
	if (!request) {
		frm.set_intro("");
		return;
	}

	if (frm.is_new() && frm.doc.is_default) {
		// The server unticks it on insert; show that before the first save.
		frm.set_value("is_default", 0);
	}
	frm.set_intro(__("This BOM is for request {0}.", [request]), "blue");

	if (frm.request_items?.request === request) return;

	const doc = await frappe.db.get_doc("Utility Service Request", request);
	frm.request_items = {
		request,
		item_codes: [...new Set((doc.items || []).map((row) => row.item_code).filter(Boolean))],
	};
}
