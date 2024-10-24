frappe.listview_settings["Sales Order"] = {
	add_fields: [
		"base_grand_total",
		"customer_name",
		"currency",
		"delivery_date",
		"per_delivered",
		"per_billed",
		"status",
		"advance_payment_status",
		"order_type",
		"name",
		"skip_delivery_note",
	],
	get_indicator: function (doc) {
		if (doc.status === "Closed") {
			// Closed
			return [__("Closed"), "green", "status,=,Closed"];
		} else if (doc.status === "On Hold") {
			// on hold
			return [__("On Hold"), "orange", "status,=,On Hold"];
		} else if (doc.status === "Completed") {
			return [__("Completed"), "green", "status,=,Completed"];
		} else if (doc.advance_payment_status === "Requested") {
			return [__("To Pay"), "gray", "advance_payment_status,=,Requested"];
		} else if (!doc.skip_delivery_note && flt(doc.per_delivered, 2) < 100) {
			if (frappe.datetime.get_diff(doc.delivery_date) < 0) {
				// not delivered & overdue
				return [
					__("Overdue"),
					"red",
					"per_delivered,<,100|delivery_date,<,Today|status,!=,Closed",
				];
			} else if (flt(doc.grand_total) === 0) {
				// not delivered (zeroount order)
				return [
					__("To Deliver"),
					"orange",
					"per_delivered,<,100|grand_total,=,0|status,!=,Closed",
				];
			} else if (flt(doc.per_billed, 2) < 100) {
				// not delivered & not billed
				return [
					__("To Deliver and Bill"),
					"orange",
					"per_delivered,<,100|per_billed,<,100|status,!=,Closed",
				];
			} else {
				// not billed
				return [
					__("To Deliver"),
					"orange",
					"per_delivered,<,100|per_billed,=,100|status,!=,Closed",
				];
			}
		} else if (
			flt(doc.per_delivered, 2) === 100 &&
			flt(doc.grand_total) !== 0 &&
			flt(doc.per_billed, 2) < 100
		) {
			// to bill
			return [
				__("To Bill"),
				"orange",
				"per_delivered,=,100|per_billed,<,100|status,!=,Closed",
			];
		} else if (doc.skip_delivery_note && flt(doc.per_billed, 2) < 100) {
			return [__("To Bill"), "orange", "per_billed,<,100|status,!=,Closed"];
		}
	},
	onload: function (listview) {
		var method =
			"erpnext.selling.doctype.sales_order.sales_order.close_or_unclose_sales_orders";

		listview.page.add_menu_item(__("Close"), function () {
			listview.call_for_selected_items(method, { status: "Closed" });
		});

		listview.page.add_menu_item(__("Re-open"), function () {
			listview.call_for_selected_items(method, { status: "Submitted" });
		});

		listview.page.add_action_item(__("Sales Invoice"), () => {
			frappe.call({
				method: "frappe.client.get_value",
				args: {
					doctype: "Utility Billing Settings",
					fieldname: "individual_invoices_for_multiple_sales_orders",
				},
				callback: function (r) {
					let create_individual_invoices =
						r.message.individual_invoices_for_multiple_sales_orders;

					if (create_individual_invoices == 1) {
						createSalesInvoices(listview);
					} else {
						erpnext.bulk_transaction_processing.create(
							listview,
							"Sales Order",
							"Sales Invoice"
						);
					}
				},
			});
		});

		listview.page.add_action_item(__("Delivery Note"), () => {
			frappe.call({
				method: "erpnext.selling.doctype.sales_order.sales_order.is_enable_cutoff_date_on_bulk_delivery_note_creation",
				callback: (r) => {
					if (r.message) {
						var dialog = new frappe.ui.Dialog({
							title: __("Select Items up to Delivery Date"),
							fields: [
								{
									fieldtype: "Date",
									fieldname: "delivery_date",
									default: frappe.datetime.add_days(
										frappe.datetime.nowdate(),
										1
									),
								},
							],
						});
						dialog.set_primary_action(__("Select"), function (values) {
							var until_delivery_date = values.delivery_date;
							erpnext.bulk_transaction_processing.create(
								listview,
								"Sales Order",
								"Delivery Note",
								{
									until_delivery_date,
								}
							);
							dialog.hide();
						});
						dialog.show();
					} else {
						erpnext.bulk_transaction_processing.create(
							listview,
							"Sales Order",
							"Delivery Note"
						);
					}
				},
			});
		});

		listview.page.add_action_item(__("Advance Payment"), () => {
			erpnext.bulk_transaction_processing.create(listview, "Sales Order", "Payment Entry");
		});
	},
};

function createSalesInvoices(listview, args) {
	let checked_items = listview.get_checked_items();
	const doc_names = [];

	checked_items.forEach((item) => {
		if (item.docstatus === 1) {
			doc_names.push(item.name);
		}
	});

	let count_of_rows = checked_items.length;

	frappe.confirm(__("Create {0} Sales Invoice(s)?", [count_of_rows]), () => {
		if (doc_names.length > 0) {
			const invoice_args = {
				source_names: doc_names,
			};

			frappe.call({
				method: "utility_billing.utility_billing.overrides.server.sales_order.enqueue_sales_invoice_creation",
				args: invoice_args,
				callback: function (response) {
					if (response.message) {
						frappe.msgprint(__(response.message));
					} else {
						frappe.msgprint(__("No valid orders to process."));
					}
				},
			});
		} else {
			frappe.msgprint(__("Selected document must be in submitted state"));
		}
	});
}