from frappe import _


def get_data():
	return {
		"fieldname": "utility_property",
		"non_standard_fieldnames": {
			"Asset": "item_code",
			"Meter Reading": "property",
		},
		"transactions": [
			{
				"label": _("Contracts"),
				"items": [
					"Contract",
				],
			},
			{
				"label": _("Assets"),
				"items": [
					"Asset",
				],
			},
			{
				"label": _("Support"),
				"items": [
					"Issue",
				],
			},
			{
				"label": _("Sales"),
				"items": [
					"Quotation",
					"Sales Order",
					"Delivery Note",
					"Sales Invoice",
				],
			},
			{
				"label": _("Utility Operations"),
				"items": [
					"Meter Reading",
					"Utility Service Request",
				],
			},
			{
				"label": _("Payments"),
				"items": [
					"Payment Entry",
					"Payment Request",
				],
			},
			{
				"label": _("Buy"),
				"items": [
					"Material Request",
					"Supplier Quotation",
					"Purchase Order",
					"Purchase Receipt",
					"Purchase Invoice",
				],
			},
		],
	}
