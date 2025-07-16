// frappe.listview_settings["Utility Service Request"] = {
// 	add_fields: [
// 		"customer",
// 		"utility_property",
// 		"utility_request_type",
// 		"per_billed",
// 		"billing_status",
// 		"status",
// 		"name",
// 	],
// 	get_indicator: function (doc) {
// 		if (doc.status === "Closed" || doc.billing_status === "Closed") {
// 			return [__("Closed"), "green", "billing_status,=,Closed"];
// 		}
// 		if (doc.status === "On Hold") {
// 			return [__("On Hold"), "orange", "status,=,On Hold"];
// 		}
// 		if (doc.billing_status === "Not Billed") {
// 			return [__("Not Billed"), "red", "billing_status,=,Not Billed"];
// 		}
// 		if (doc.billing_status === "Partly Billed") {
// 			return [__("Partly Billed"), "orange", "billing_status,=,Partly Billed"];
// 		}
// 		if (doc.billing_status === "Fully Billed") {
// 			return [__("Fully Billed"), "green", "billing_status,=,Fully Billed"];
// 		}
// 	},
// };
