from frappe import _

def get_data():
    return {
        "fieldname": "name", 
        "internal_links": {
            "Item": "item",
            "Customer": "customer",
        },
        "non_standard_fieldnames": {
            "Asset": "item_code",
            "Meter Reading": "property",
            "Utility Service Request": "utility_property",
            "Quotation": "utility_property",
            "Sales Order": "utility_property",
            "Delivery Note": "utility_property",
            "Sales Invoice": "utility_property",
            "Material Request": "utility_property",
            "Supplier Quotation": "utility_property",
            "Purchase Order": "utility_property",
            "Purchase Receipt": "utility_property",
            "Purchase Invoice": "utility_property",
            "Payment Entry": "utility_property",
            "Payment Request": "utility_property",
        },
        "transactions": [
            {
                "label": _("Utility Operations"),
                "items": [
                    "Meter Reading",
                    "Utility Service Request",
                ],
            },
            {
                "label": _("Assets"),
                "items": [
                    "Item",
                    "Asset",
                ],
            },
            {
                "label": _("Customer"),
                "items": [
                    "Customer",
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
                "label": _("Buy"),
                "items": [
                    "Material Request",
                    "Supplier Quotation",
                    "Request for Quotation",
                    "Purchase Order",
                    "Purchase Receipt",
                    "Purchase Invoice",
                ],
            },
            {
                "label": _("Payments"),
                "items": [
                    "Payment Entry",
                    "Payment Request",
                ],
            },
        ],
    }
