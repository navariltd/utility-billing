# Copyright (c) 2024, Navari and contributors
# For license information, please see license.txt
import frappe
from frappe.model.document import Document
from frappe.utils import nowdate
from frappe.query_builder import DocType
from frappe.query_builder.functions import Sum
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

    for rate in meter_reading.rates:
        sales_order.append(
            "items",
            {
                "item_code": rate.item_code,
                "qty": round(rate.qty),
                "rate": rate.rate,
                "amount": rate.amount,
                "block": rate.block,
                "delivery_date": nowdate(),
            },
        )

    for i in meter_reading.items:
        _, prev_reading = get_previous_invoice_reading(i.meter_number)
        prev_consumption = get_previous_consumption(i.meter_number)
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
                "previous_consumption": prev_consumption,
            },
        )
    sales_order.insert()

    return sales_order


@frappe.whitelist()
def get_previous_consumption(meter_number):
    """Fetch the sum of previous readings for the specified meter number sharing the same parent."""
    parent, _ = get_previous_invoice_reading(meter_number)
    meter_reading = DocType("Sales Invoice Meter Reading")
    previous_consumption = (
        frappe.qb
        .from_(meter_reading)
        .where(meter_reading.parent == parent)
        .select(Sum(meter_reading.current_reading - meter_reading.previous_reading))
    ).run()
    return previous_consumption[0][0] if previous_consumption else 0


@frappe.whitelist()
def get_previous_invoice_reading(meter_number):
    """Fetch the previous reading and its parent for the specified meter number."""
    previous_reading = frappe.get_all(
        "Sales Invoice Meter Reading",
        filters={"meter_number": meter_number},
        fields=["current_reading", "creation", "parent"],
        order_by="creation desc",
        limit_page_length=1,
    )

    if previous_reading:
        return previous_reading[0].parent, previous_reading[0].current_reading
    else:
        return "None", 0


@frappe.whitelist()
def get_previous_reading(meter_number):
    """Fetch the previous reading for the specified meter number."""
    previous_reading = frappe.get_all(
        "Meter Reading Item",
        filters={"meter_number": meter_number},
        fields=["current_reading", "creation"],
        order_by="creation desc",
        limit_page_length=1,
    )

    return previous_reading[0].current_reading if previous_reading else 0


@frappe.whitelist()
def get_customer_details(customer):
    """Fetch all customer details, including the default price list and other fields."""

    customer_doc = frappe.get_doc("Customer", customer)

    if not customer_doc.default_price_list:
        customer_doc.default_price_list = frappe.db.get_value(
            "Customer Group", customer_doc.customer_group, "default_price_list"
        )

    return customer_doc.as_dict()
