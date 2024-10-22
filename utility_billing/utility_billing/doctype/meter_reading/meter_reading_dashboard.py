from frappe import _
def get_data():
    return {
        "fieldname": "name", 
        "transactions": [
            {
                "label": _("Related Documents"),
                "items": [
                    "Sales Order",
                ],
            },
        ],
        "dynamic_links": {
            "Sales Order": ["meter_readings", "meter_reading"]  
        }
    }
