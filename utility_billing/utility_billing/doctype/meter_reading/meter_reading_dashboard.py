from frappe import _


def get_data():
    return {
        "fieldname": "meter_reading",
        "dynamic_links": {
            "Sales Order": ["meter_readings", "meter_reading"],
            "Sales Invoice": ["meter_readings", "meter_reading"],
        },
        "transactions": [
            {
                "label": _("Related Documents"),
                "items": [
                    "Sales Order",
                    "Sales Invoice",
                ],
            },
        ],
    }
