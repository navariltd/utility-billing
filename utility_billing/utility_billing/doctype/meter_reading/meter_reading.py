# Copyright (c) 2024, Navari and contributors
# For license information, please see license.txt
import frappe
from frappe.model.document import Document
from frappe.query_builder import DocType
from frappe.query_builder.functions import Sum
from frappe.utils import nowdate
from erpnext.controllers.accounts_controller import AccountsController

from ..utility_service_request.utility_service_request import get_item_details
from ...utils.create_meter_reading_rates import create_meter_reading_rates


class MeterReading(Document):
    def validate(self):
        create_meter_reading_rates(self, self.price_list, self.date)

    def on_submit(self):
        settings = frappe.get_single("Utility Billing Settings")
        existing_sales_order = frappe.db.exists(
            {
                "doctype": "Sales Order Meter Reading",
                "parenttype": "Sales Order",
                "meter_reading": self.name,
            }
        )
        if not existing_sales_order:
            if settings.sales_order_creation_state == "Draft":
                sales_order = create_sales_order(self)
            else:
                sales_order = create_sales_order(self)
                sales_order.submit()


def create_sales_order(meter_reading):
    """Create a Sales Order based on the Meter Reading."""
    sales_order = frappe.get_doc(
        {
            "doctype": "Sales Order",
            "customer": meter_reading.customer,
            "meter_readings": [],
            "items": [],
            "order_type": "Sales",
            "selling_price_list": meter_reading.price_list,
        }
    )
    utility_property = frappe.get_value("Customer", meter_reading.customer, "utility_property")
    if utility_property:
        sales_order.utility_property = utility_property

    for rate in meter_reading.rates:
        rate_dict = rate.as_dict()
        rate_dict["delivery_date"] = nowdate()
        sales_order.append("items", rate_dict)
        

    for i in meter_reading.items:
        prev_reading = get_previous_invoice_reading(i.item_code, meter_reading.customer)
        sales_order.append(
            "meter_readings",
            {
                "item_code": i.item_code,
                "meter_number": i.meter_number,
                "meter_reading": meter_reading.name,
                "uom": i.uom,
                "stock_uom": i.stock_uom,
                "current_reading": i.current_reading,
                "previous_reading": prev_reading,
                "consumption": i.consumption,
            },
        )
    
    sales_order.insert() 
    AccountsController.append_taxes_from_item_tax_template(sales_order)
    sales_order.save()

    return sales_order

@frappe.whitelist()
def get_previous_invoice_reading(item_code, customer):
    """Fetch the last submitted invoice's current reading for the specified item and customer."""
    
    latest_invoice = frappe.get_value("Sales Invoice", filters={"customer": customer, "docstatus": 1},
                                      fieldname="name", order_by="creation desc")
    
    if not latest_invoice:
        return 0  
    
    previous_reading = frappe.get_value("Sales Invoice Meter Reading", filters={"parent": latest_invoice, "item_code": item_code},
                                       fieldname="current_reading", order_by="creation desc")
    
    return previous_reading or 0  


@frappe.whitelist()
def get_customer_details(customer):
    """Fetch all customer details, including the default price list and other fields."""

    customer_doc = frappe.get_doc("Customer", customer)

    if not customer_doc.default_price_list:
        customer_doc.default_price_list = frappe.db.get_value(
            "Customer Group", customer_doc.customer_group, "default_price_list"
        )

    return customer_doc.as_dict()
