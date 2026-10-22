frappe.ui.form.on("Warranty Claim", {
	refresh: function (frm) {
		set_serial_no_query(frm);
	},

	item_code: function (frm) {
		frm.set_value("serial_no", "");
		set_serial_no_query(frm);
	},

	company: function (frm) {
		frm.set_value("serial_no", "");
		set_serial_no_query(frm);
	},
});

async function set_serial_no_query(frm) {
	const closed_claims = await frappe.db.get_list("Warranty Claim", {
		filters: {
			status: "Closed",
			docstatus: ["<", 2],
			name: ["!=", frm.doc.name],
		},
		fields: ["serial_no"],
		limit_page_length: 0,
	});

	const closed_serials = [
		...new Set(closed_claims.map((claim) => claim.serial_no).filter(Boolean)),
	];

	console.log("Closed serials:", closed_serials);

	let filters = {
		status: "Active",
	};

	if (frm.doc.item_code) {
		filters.item_code = frm.doc.item_code;
	}

	if (frm.doc.company) {
		filters.company = frm.doc.company;
	}

	if (closed_serials.length) {
		filters.name = ["not in", closed_serials];
	}

	console.log("Serial number filters:", filters);

	frm.set_query("serial_no", function () {
		return {
			filters: filters,
		};
	});
}
