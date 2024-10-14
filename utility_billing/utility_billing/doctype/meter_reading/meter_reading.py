# Copyright (c) 2024, Navari and contributors
# For license information, please see license.txt
import frappe
from frappe.model.document import Document
from frappe.utils import nowdate


class MeterReading(Document):
    def validate(self):
        create_meter_reading_rates(self)
        settings = frappe.get_single("Utility Billing Settings")
        if settings.sales_order_creation_state == "Draft":
            create_sales_order(self)

    def after_insert(self):
        create_meter_reading_rates(self)
        self.save()

    def before_submit(self):
        settings = frappe.get_single("Utility Billing Settings")
        if settings.sales_order_creation_state == "Submitted":
            create_sales_order(self)


def create_meter_reading_rates(meter_reading):
    """Create Meter Reading Rate documents from the Meter Reading and append to its rates child table."""

    meter_reading.set("rates", [])
    for item in meter_reading.items:
        item_prices = frappe.get_list(
            "Item Price",
            filters={
                "item_code": item.item_code,
                "price_list": meter_reading.price_list,
            },
            fields=["name", "tariffs"],
        )

        if not item_prices:
            frappe.throw(
                ("No pricing available for Item {0} and Price List {1}").format(
                    item.item_code, meter_reading.price_list
                )
            )

        total_consumption = item.consumption

        for item_price in item_prices:
            item_price_doc = frappe.get_doc("Item Price", item_price.name)

            for tariff in item_price_doc.tariffs:
                if total_consumption <= 0:
                    break

                slab_quantity = min(
                    total_consumption, tariff.upper_limit - tariff.lower_limit
                )

                if slab_quantity <= 0:
                    continue

                rate = tariff.rate
                amount = slab_quantity * rate

                meter_reading.append(
                    "rates",
                    {
                        "meter_reading_item": item.name,
                        "item_code": item.item_code,
                        "qty": slab_quantity,
                        "amount": amount,
                        "rate": rate,
                    },
                )

                total_consumption -= slab_quantity


def create_sales_order(meter_reading):
    sales_order = frappe.get_doc(
        {"doctype": "Sales Order", "customer": meter_reading.customer, "items": []}
    )

    for item in meter_reading.items:
        meter_reading_rate = frappe.get_value(
            "Meter Reading Rate", {"meter_reading_item": item.name}, ["qty", "amount"]
        )

        qty = meter_reading_rate[0] if meter_reading_rate else item.consumption
        amount = meter_reading_rate[1] if meter_reading_rate else 0

        sales_order.append(
            "items",
            {
                "item_code": item.item_code,
                "meter_number": item.meter_number,
                "previous_reading": item.previous_reading,
                "current_reading": item.current_reading,
                "qty": qty,
                "rate": amount,
                "delivery_date": nowdate(),
            },
        )

    sales_order.insert()


@frappe.whitelist()
def get_previous_reading(meter_number):
    """Fetch all previous readings for the specified meter number."""
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
    """Fetch customer name and price list."""
    customer_details = frappe.db.get_value(
        "Customer",
        customer,
        ["customer_name", "default_price_list", "territory"],
        as_dict=True,
    )
    if customer_details:
        if not customer_details.default_price_list:
            customer_group = frappe.db.get_value("Customer", customer, "customer_group")
            customer_details.default_price_list = frappe.db.get_value(
                "Customer Group", customer_group, "default_price_list"
            )
    return customer_details or {}
