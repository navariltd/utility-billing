import frappe


@frappe.whitelist()
def create_meter_reading_rates(meter_reading, price_list, reading_date):
    """Create Meter Reading Tariff Rate documents based on the Meter Reading date and append to its rates child table."""
    meter_reading.set("rates", [])

    for item in meter_reading.items:
        item_prices = get_item_prices(item.item_code, price_list, reading_date)

        if not item_prices:
            raise_no_pricing_error(item.item_code, price_list, reading_date)

        total_consumption = item.consumption

        for item_price in item_prices:
            item_price_doc = frappe.get_doc("Item Price", item_price.name)

            if is_fixed_meter_charge(item_price_doc):
                process_fixed_meter_charge(
                    meter_reading, item, item_price_doc, total_consumption
                )
            else:
                process_tariff_charges(
                    meter_reading, item, item_price_doc, total_consumption
                )


def get_item_prices(item_code, price_list, reading_date):
    """Fetch item prices for the given item code and reading date."""
    return frappe.get_list(
        "Item Price",
        filters={
            "item_code": item_code,
            "price_list": price_list,
            "valid_from": ("<=", reading_date),
            "valid_upto": (">=", reading_date),
        },
        fields=["name", "tariffs", "is_fixed_meter_charge"],
    )


def raise_no_pricing_error(item_code, price_list, reading_date):
    """Raise an error if no valid pricing is available."""
    frappe.throw(
        ("No valid pricing available for Item {0} on Price List {1} as of {2}").format(
            item_code, price_list, reading_date
        )
    )


def is_fixed_meter_charge(item_price_doc):
    """Check if the item price document has a fixed meter charge."""
    return item_price_doc.is_fixed_meter_charge == 1


def process_fixed_meter_charge(meter_reading, item, item_price_doc, total_consumption):
    """Process fixed meter charges and append rates to meter reading."""
    first_tariff = item_price_doc.tariffs[0]

    if total_consumption > first_tariff.upper_limit:
        raise_exceeds_upper_limit_error(item.item_code, first_tariff.upper_limit)

    slab_quantity = first_tariff.upper_limit
    rate = first_tariff.rate
    amount = slab_quantity * rate

    append_meter_reading_rate(
        meter_reading, item, first_tariff.block, slab_quantity, rate, amount
    )


def raise_exceeds_upper_limit_error(item_code, upper_limit):
    """Raise an error if the consumption exceeds the upper limit of a fixed charge slab."""
    frappe.throw(
        (
            "Consumption for Item {0} exceeds the upper limit of the fixed charge slab ({1})."
        ).format(item_code, upper_limit)
    )


def process_tariff_charges(meter_reading, item, item_price_doc, total_consumption):
    """Process non-fixed tariff charges based on consumption."""
    for tariff in item_price_doc.tariffs:
        if total_consumption <= 0:
            break

        slab_quantity = calculate_slab_quantity(total_consumption, tariff)

        if slab_quantity <= 0:
            continue

        rate = tariff.rate
        amount = slab_quantity * rate

        append_meter_reading_rate(
            meter_reading, item, tariff.block, slab_quantity, rate, amount
        )

        total_consumption -= slab_quantity


def calculate_slab_quantity(total_consumption, tariff):
    """Calculate the quantity for a specific tariff slab."""
    return min(total_consumption, tariff.upper_limit - tariff.lower_limit)


def append_meter_reading_rate(meter_reading, item, block, slab_quantity, rate, amount):
    """Append a rate entry to the meter reading."""
    meter_reading.append(
        "rates",
        {
            "meter_reading_item": item.name,
            "item_code": item.item_code,
            "block": block,
            "qty": slab_quantity,
            "amount": amount,
            "rate": rate,
        },
    )
