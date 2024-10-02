# Copyright (c) 2024, Navari and contributors
# For license information, please see license.txt
import frappe
from frappe.model.document import Document


class MeterReading(Document):
    def on_submit(self):
        # Get settings from Utility Billing Settings
        settings = frappe.get_single("Utility Billing Settings")
        sales_order_state = settings.sales_order_creation_state or "Draft"

        # Create Sales Order
        sales_order = frappe.new_doc("Sales Order")
        sales_order.customer = self.customer
        sales_order.transaction_date = self.date
        sales_order.currency = self.currency
        sales_order.price_list = self.price_list
        sales_order.territory = self.territory

        # Add Meter Reading Items to Sales Order Items
        for item in self.items:
            sales_order_item = sales_order.append("items", {})
            sales_order_item.item_code = item.item_code
            sales_order_item.item_name = item.item_name
            sales_order_item.description = item.description
            sales_order_item.uom = item.uom
            sales_order_item.stock_uom = item.stock_uom
            sales_order_item.qty = item.consumption
            sales_order_item.warehouse = item.delivery_warehouse

            # Calculate rate and amount for the item based on tariff rates
            rates = frappe.get_all(
                "Meter Reading Rate",
                filters={"meter_reading_item": item.name},
                fields=["quantity", "rate"],
            )
            total_amount = sum(rate["quantity"] * rate["rate"] for rate in rates)
            sales_order_item.rate = 0  # Since rate is calculated separately
            sales_order_item.amount = total_amount

        # Save Sales Order in Draft or Submit it
        sales_order.flags.ignore_permissions = True
        if sales_order_state == "Draft":
            sales_order.save()
        else:
            sales_order.submit()
