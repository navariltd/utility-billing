from frappe.model.document import Document
import frappe

def before_validate(doc: Document, method: str) -> None:
    """Intercepts submit event for document"""
    unique_sales_orders = {item.sales_order for item in doc.items if item.sales_order}
    for sales_order in unique_sales_orders:
        copy_meter_reading_from_sales_order(doc, sales_order)

def copy_meter_reading_from_sales_order(doc: Document, sales_order_name: str) -> None:
    """Copies meter_readings tables from the linked Sales Order."""
    sales_order = frappe.get_doc("Sales Order", sales_order_name)
    
    if hasattr(sales_order, "meter_readings"):
        if not doc.meter_readings:
            doc.meter_readings = []
        for reading in sales_order.meter_readings:
            reading_dict = reading.as_dict()
            reading_dict.pop("name", None)
            
            if not any(existing_reading for existing_reading in doc.meter_readings if existing_reading.meter_reading == reading_dict.get("meter_reading")):
                new_reading = doc.append("meter_readings", {})
                new_reading.update(reading_dict)
