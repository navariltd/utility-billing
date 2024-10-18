import frappe
from frappe.query_builder import DocType


@frappe.whitelist(allow_guest=True)
def drop_meter_reading():
    try:
        MeterReading = DocType("Meter Reading")
        MeterReadingItem = DocType("Meter Reading Item")
        MeterReadingRate = DocType("Meter Reading Rate")

        frappe.qb.from_(MeterReading).delete().run()
        frappe.qb.from_(MeterReadingItem).delete().run()
        frappe.qb.from_(MeterReadingRate).delete().run()

        frappe.db.commit()

        return {
            "status": "success",
            "message": "All entries in Meter Reading, Meter Reading Item, and Meter Reading Rate have been successfully deleted.",
        }

    except Exception as e:
        frappe.log_error(
            f"An error occurred while deleting records: {str(e)}", "Drop Reading Error"
        )
        return {"status": "error", "message": str(e)}
