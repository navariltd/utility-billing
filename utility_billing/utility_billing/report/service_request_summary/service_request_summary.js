// Copyright (c) 2025, Navari Ltd and contributors
// For license information, please see license.txt

frappe.query_reports["Service Request Summary"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{
			fieldname: "customer",
			label: __("Customer"),
			fieldtype: "Link",
			options: "Customer",
		},
		{
			fieldname: "customer_group",
			label: __("Customer Group"),
			fieldtype: "Link",
			options: "Customer Group",
		},
		{
			fieldname: "territory",
			label: __("Territory"),
			fieldtype: "Link",
			options: "Territory",
		},
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
		},
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: "\nDraft\nOn Hold\nTo Pay\nTo Bill\nTo Deliver\nCompleted\nCancelled\nClosed",
			default: "",
		},
		{
			fieldname: "request_status",
			label: __("Request Status"),
			fieldtype: "Select",
			options: "\nSite Survey Created\nSite Survey Completed\nBOM Created\nBOM Completed",
			default: "",
		},
		{
			fieldname: "request_type",
			label: __("Request Type"),
			fieldtype: "Link",
			options: "Issue Type",
		},
		{
			fieldname: "utility_bill_structure",
			label: __("Utility Bill Structure"),
			fieldtype: "Link",
			options: "Utility Bill Structure",
		},
	],

	formatter: function (value, row, column, data, default_formatter) {
		if (column.fieldname && column.fieldname.toLowerCase().includes("percent")) {
			const percent = Math.min(Math.max(parseFloat(value) || 0, 0), 100);
			let color;

			if (percent >= 90) {
				color = "#2ecc71";
			} else if (percent >= 50) {
				color = "#f39c12";
			} else {
				color = "#e74c3c";
			}

			const textInside = percent > 40;
			const percentStr = percent.toFixed(2);

			return `
				<div style="width: 100%; background-color: #e0e0e0; border-radius: 8px; overflow: hidden; position: relative; height: 20px;">
					<div style="
						width: ${percent}%;
						background-color: ${color};
						height: 100%;
						transition: width 0.3s ease;
						text-align: ${textInside ? "center" : "right"};
						color: white;
						font-size: 12px;
						line-height: 20px;
						padding-right: ${textInside ? "0" : "5px"};
					">
						${textInside ? `${percentStr}%` : ""}
					</div>
					${
						!textInside
							? `<div style="position: absolute; right: 5px; top: 0; font-size: 12px; line-height: 20px; color: #333;">${percentStr}%</div>`
							: ""
					}
				</div>`;
		}

		if (column.fieldname === "status" && value) {
			const status_colors = {
				Draft: "#444444",
				"On Hold": "#b9770e",
				"To Pay": "#21618c",
				"To Bill": "#b7950b",
				"To Deliver": "#5b2c6f",
				Completed: "#196f3d",
				Cancelled: "#922b21",
				Closed: "#566573",
			};
			const color = status_colors[value] || "#212f3c";
			value = `<span style="color:${color};font-weight:bold;font-size:12px;">${value}</span>`;
		}

		return default_formatter(value, row, column, data);
	},
};
