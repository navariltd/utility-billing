"""Read the Item Prices generated for a service request and render a summary.

Item Prices are the source of truth for the rent schedule, so this module reads
them back and hands them to ``item_price_summary_html``, which renders them
grouped by property as an editable table. It is used by the HTML field on
``Utility Service Request`` instead of storing a duplicate schedule table.

Grouping works off the property's **service item**: each property owns an item
named after it, so an Item Price is attributed to a property by its
``item_code``. No extra tagging on ``Item Price`` is required.

Nothing is written while typing: the surrounding page reads the inputs and
saves them through ``item_price_summary_actions.save_item_price_schedule``.
"""

import frappe

from utility_billing.utility_billing.utils import item_price_summary_html


def get_property_item_codes(properties: list[str]) -> dict[str, str]:
    """Return the service item of each property.

    Args:
        properties: ``Utility Property`` names.

    Returns:
        Mapping of property name to service item code, omitting properties
        without a service item.
    """
    if not properties:
        return {}

    rows = frappe.get_all(
        "Utility Property",
        filters={"name": ("in", list(properties))},
        fields=["name", "service_item"],
    )

    return {
        row["service_item"]: row["name"]
        for row in rows
        if row.get("service_item")
    }


def get_created_prices(item_code: str, price_list: str | None = None) -> list[dict]:
    """Return the Item Prices of an item, ordered by date.

    Args:
        item_code: Item whose prices are read.
        price_list: Optional price list filter.

    Returns:
        Item Price rows with the item, customer, dates and rate.
    """
    filters = {"item_code": item_code}
    if price_list:
        filters["price_list"] = price_list

    return frappe.get_all(
        "Item Price",
        filters=filters,
        fields=[
            "name",
            "item_code",
            "customer",
            "price_list",
            "valid_from",
            "valid_upto",
            "price_list_rate",
        ],
        order_by="valid_from asc",
    )


def build_schedule_html(
    properties: list[str],
    price_list: str | None = None,
    property_periods: dict | None = None,
    customer: str | None = None,
    editable: bool = True,
) -> str:
    """Render the Item Prices of the given properties as HTML.

    Args:
        properties: Properties to render.
        price_list: Optional price list filter.
        property_periods: Optional mapping of property name to its
            ``(start_date, end_date)`` contract period, used by the editor to
            validate that a manual schedule covers the whole contract.
        customer: Customer used as the default for newly added periods.
        editable: Whether the periods may be edited. ``False`` renders the
            summary as a read-only view.

    Returns:
        HTML markup listing each property with its rent periods.
    """
    # `get_property_item_codes` returns item -> property; invert for lookup.
    item_by_property = {
        property_name: item_code
        for item_code, property_name in get_property_item_codes(properties).items()
    }
    periods = property_periods or {}

    sections = []
    for property_name in properties:
        item_code = item_by_property.get(property_name)
        start_date, end_date = periods.get(property_name, (None, None))
        sections.append(
            {
                "property": property_name,
                "item_code": item_code,
                "price_list": price_list,
                "customer": customer,
                "start_date": start_date,
                "end_date": end_date,
                "prices": get_created_prices(item_code, price_list) if item_code else [],
            }
        )

    return item_price_summary_html.render_schedule(sections, editable=editable)

