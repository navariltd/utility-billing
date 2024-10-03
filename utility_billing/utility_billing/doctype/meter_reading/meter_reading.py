# Copyright (c) 2024, Navari and contributors
# For license information, please see license.txt
import frappe
from frappe.model.document import Document
from frappe.utils import nowdate


class MeterReading(Document):
    def validate(self):
        settings = frappe.get_single("Utility Billing Settings")
        if settings.sales_order_creation_state == "Draft":
            create_sales_order(self)

    def after_insert(self):
        create_meter_reading_rates(self)

    def before_submit(self):
        settings = frappe.get_single("Utility Billing Settings")
        if settings.sales_order_creation_state == "Submitted":
            create_sales_order(self)


def create_meter_reading_rates(meter_reading):
    """Create Meter Reading Rate documents from the Meter Reading."""
    for item in meter_reading.items:
        existing_rates = frappe.get_list(
            "Meter Reading Rate", filters={"meter_reading_item": item.name}
        )
        if existing_rates:
            continue

        rate = 1
        quantity = 1
        amount = quantity * rate
        rate_doc = frappe.get_doc(
            {
                "doctype": "Meter Reading Rate",
                "meter_reading_item": item.name,
                "item_code": item.item_code,
                "quantity": quantity,
                "amount": amount,
                "rate": rate,
                "meter_reading": meter_reading.name,
            }
        )
        rate_doc.insert()


def create_sales_order(meter_reading):
    sales_order = frappe.get_doc(
        {"doctype": "Sales Order", "customer": meter_reading.customer, "items": []}
    )
    for item in meter_reading.items:
        sales_order.append(
            "items",
            {
                "item_code": item.item_code,
                "qty": item.consumption,
                "delivery_date": nowdate(),
            },
        )

    sales_order.insert()


@frappe.whitelist()
def get_previous_reading(meter_number):
    """Fetch all previous readings for the specified meter number using SQL."""
    query = """
        SELECT current_reading, creation
        FROM `tabMeter Reading Item`
        WHERE meter_number = %s
        ORDER BY creation DESC
    """
    previous_readings = frappe.db.sql(query, (meter_number,), as_dict=True)
    return previous_readings[0].current_reading if previous_readings else 0


@frappe.whitelist()
def get_customer_details(customer):
    """Fetch customer name and price list."""
    customer_details = frappe.db.get_value(
        "Customer", customer, ["customer_name", "default_price_list"], as_dict=True
    )
    if customer_details:
        if not customer_details.default_price_list:
            customer_group = frappe.db.get_value("Customer", customer, "customer_group")
            customer_details.default_price_list = frappe.db.get_value(
                "Customer Group", customer_group, "default_price_list"
            )
    return customer_details or {}
