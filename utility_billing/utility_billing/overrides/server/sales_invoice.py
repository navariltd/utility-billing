import frappe
from erpnext.controllers.accounts_controller import AccountsController
from erpnext.controllers.taxes_and_totals import calculate_taxes_and_totals
from frappe.model.document import Document
from frappe.utils import add_days
from ...utils.update_service_request import update_billing_status
from ...utils.utils import (
	sync_meter_readings,
)


def validate(doc: Document, method: str) -> None:
	sync_meter_readings(doc)

def before_validate(doc: Document, method: str) -> None:
    """Intercepts submit event for document"""
    if not doc.taxes:
        AccountsController.append_taxes_from_item_tax_template(doc)
        calculate_taxes_and_totals(doc)
    unique_sales_orders = {
        item.sales_order
        for item in frappe.get_all(
            "Sales Invoice Item",
            filters={"parent": doc.name, "sales_order": ["is", "set"]},
            fields=["sales_order"],
        )
    }   

    for sales_order in unique_sales_orders:
        map_sales_order_meter_readings_to_invoice(sales_order, doc)


def map_sales_order_meter_readings_to_invoice(sales_order_name, target_doc):
    """Map all fields from Sales Order Meter Reading to Sales Invoice Meter Reading."""
    sales_order = frappe.get_doc("Sales Order", sales_order_name)
    meter_readings = sales_order.get("meter_readings")
    target_doc.set("meter_readings", [])
    if sales_order.utility_property:
        target_doc.utility_property = sales_order.utility_property
    if sales_order.utility_service_request:
        target_doc.utility_service_request = sales_order.utility_service_request

    for reading in meter_readings:
        new_reading_data = reading.as_dict()
        new_reading_data.pop("name", None)
        new_reading = target_doc.append("meter_readings", new_reading_data)
        new_reading.parent = target_doc.name

def on_submit(doc: Document, method: str) -> None:
    """Intercepts submit event for document"""
    if doc.utility_service_request:
        pass
        # update_billing_status(doc.utility_service_request)