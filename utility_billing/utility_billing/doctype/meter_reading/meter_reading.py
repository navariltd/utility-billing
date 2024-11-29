# Copyright (c) 2024, Navari and contributors
# For license information, please see license.txt
import frappe
from frappe.model.document import Document
from frappe.query_builder import DocType
from frappe.utils import nowdate
from erpnext.controllers.accounts_controller import AccountsController
from frappe.query_builder import DocType
from pypika import Order

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
        prev_reading = get_previous_invoice_reading(i.item_code, meter_reading.customer, i.meter_number)
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
def get_previous_invoice_reading(item_code, customer, meter_number=None):
    """Fetch the latest reading for the specified customer, item, and optional meter number."""
    
    SalesInvoiceMeterReading = DocType("Sales Invoice Meter Reading")
    SalesInvoice = DocType("Sales Invoice")
    
    query = (
        frappe.qb.from_(SalesInvoiceMeterReading)
        .join(SalesInvoice).on(SalesInvoice.name == SalesInvoiceMeterReading.parent) 
        .select(SalesInvoiceMeterReading.current_reading)
        .where(SalesInvoice.customer == customer)
        .where(SalesInvoiceMeterReading.item_code == item_code)
        .where(SalesInvoice.docstatus == 1)
    )
    
    if meter_number:
        query = query.where(SalesInvoiceMeterReading.meter_number == meter_number)
    else:
        query = query.where(SalesInvoiceMeterReading.meter_number.isnull())
    
    query = query.orderby(SalesInvoiceMeterReading.creation, order=Order.desc)
    result = query.limit(1).run()

    return result[0][0] if result else 0


@frappe.whitelist()
def get_customer_details(customer):
    """Fetch all customer details, including the default price list and other fields."""

    customer_doc = frappe.get_doc("Customer", customer)

    if not customer_doc.default_price_list:
        customer_doc.default_price_list = frappe.db.get_value(
            "Customer Group", customer_doc.customer_group, "default_price_list"
        )

    return customer_doc.as_dict()


@frappe.whitelist()
def get_serial_numbers_from_warranty_claims(customer):
    """
    Fetch serial numbers from closed Warranty Claims for the given customer and item.
    """
    serial_numbers = frappe.get_all(
        "Warranty Claim",
        filters={
            "customer": customer,
            "status": "Closed",
        },
        fields=["serial_no"],
    )
    serial_list = []
    for claim in serial_numbers:
        if claim.get("serial_no"):
            serial_list.extend(claim["serial_no"].split("\n"))

    return list(set(serial_list)) 
