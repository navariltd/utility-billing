# Copyright (c) 2024, Navari and contributors
# For license information, please see license.txt
import frappe
from frappe.model.document import Document


class MeterReading(Document):
    def before_submit(self):
        for item in self.items:
            # Fetch previous reading
            previous_reading = frappe.db.get_value(
                "Meter Reading Item",
                {"item_code": item.item_code, "customer": self.customer},
                "current_reading",
                order_by="modified desc",
            )
            item.previous_reading = previous_reading or 0

            # Calculate consumption
            item.consumption = item.current_reading - item.previous_reading

            # Apply rates based on consumption
            apply_meter_reading_rates(item)


def apply_meter_reading_rates(item):
    # Tariff-based calculation logic
    tariff_blocks = frappe.get_list(
        "Item Price Tariff",
        filters={"item_code": item.item_code},
        order_by="lower_limit asc",
    )

    remaining_consumption = item.consumption
    for block in tariff_blocks:
        rate = block.rate
        lower_limit = block.lower_limit
        upper_limit = block.upper_limit

        # Determine quantity for this block
        if remaining_consumption <= upper_limit:
            quantity = remaining_consumption
        else:
            quantity = upper_limit - lower_limit

        # Calculate amount for this block
        amount = quantity * rate
        # Create Meter Reading Rate entry
        item.append(
            "rates",
            {
                "item_code": item.item_code,
                "quantity": quantity,
                "rate": rate,
                "amount": amount,
            },
        )

        remaining_consumption -= quantity
        if remaining_consumption <= 0:
            break
