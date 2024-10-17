import frappe


def create_meter_reading_rates(meter_reading, price_list, reading_date):
    """Create Meter Reading Rate documents based on the Meter Reading date and append to its rates child table."""
    meter_reading.set("rates", [])

    for item in meter_reading.items:
        item_prices = frappe.get_list(
            "Item Price",
            filters={
                "item_code": item.item_code,
                "price_list": price_list,
                "valid_from": ("<=", reading_date),
                "valid_upto": (">=", reading_date),
            },
            fields=["name", "tariffs"],
        )

        if not item_prices:
            frappe.throw(
                (
                    "No valid pricing available for Item {0} on Price List {1} as of {2}"
                ).format(item.item_code, price_list, reading_date)
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
                        "block": tariff.block,
                        "qty": slab_quantity,
                        "amount": amount,
                        "rate": rate,
                    },
                )

                total_consumption -= slab_quantity
