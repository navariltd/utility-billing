import frappe

@frappe.whitelist(allow_guest=True)  
def drop_meter_reading():
    try:
        meter_readings = frappe.get_all("Meter Reading", pluck="name")
        for reading in meter_readings:
            frappe.delete_doc("Meter Reading", reading)

        meter_reading_items = frappe.get_all("Meter Reading Item", pluck="name")
        for item in meter_reading_items:
            frappe.delete_doc("Meter Reading Item", item)

        meter_reading_rates = frappe.get_all("Meter Reading Rate", pluck="name")
        for rate in meter_reading_rates:
            frappe.delete_doc("Meter Reading Rate", rate)

        frappe.db.commit()

        return {
            "status": "success",
            "message": "All entries in Meter Reading, Meter Reading Item, and Meter Reading Rate have been successfully deleted."
        }
    
    except Exception as e:
        frappe.log_error(f"An error occurred while deleting records: {str(e)}", "Drop Reading Error")
        return {"status": "error", "message": str(e)}
