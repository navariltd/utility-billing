import frappe


def create_meter_reading_rates(meter_reading, price_list, reading_date):
    """Create Meter Reading Tariff Rate documents based on the Meter Reading date and append to its rates child table."""
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
            fields=["name", "tariffs", "is_fixed_meter_charge"],
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

            is_fixed_meter_charge = item_price_doc.is_fixed_meter_charge

            if is_fixed_meter_charge == 1:
                first_tariff = item_price_doc.tariffs[0]

                if total_consumption > first_tariff.upper_limit:
                    frappe.throw(
                        (
                            "Consumption for Item {0} exceeds the upper limit of the fixed charge slab ({1})."
                        ).format(item.item_code, first_tariff.upper_limit)
                    )

                slab_quantity = first_tariff.upper_limit
                rate = first_tariff.rate
                amount = slab_quantity * rate

                meter_reading.append(
                    "rates",
                    {
                        "meter_reading_item": item.name,
                        "item_code": item.item_code,
                        "block": first_tariff.block,
                        "qty": slab_quantity,
                        "amount": amount,
                        "rate": rate,
                    },
                )
            else:
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
