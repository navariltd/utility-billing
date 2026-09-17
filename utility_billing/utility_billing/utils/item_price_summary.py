"""Read-only summary of the Item Prices generated for a service request.

Item Prices are the source of truth for the rent schedule, so this module reads
them back and renders them grouped by property. It is used by the HTML field on
``Utility Service Request`` instead of storing a duplicate schedule table.
"""

import frappe
from frappe import _


def get_created_prices(utility_property: str, price_list: str | None = None) -> list[dict]:
    """Return the generated Item Prices of a property, ordered by date.

    Args:
        utility_property: ``Utility Property`` name.
        price_list: Optional price list filter.

    Returns:
        Item Price rows with the item, customer, dates and rate.
    """
    if not frappe.db.has_column("Item Price", "custom_utility_property"):
        return []

    filters = {"custom_is_rent_schedule": 1, "custom_utility_property": utility_property}
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
            "custom_utility_property",
        ],
        order_by="valid_from asc",
    )


def get_all_created_prices(properties: list[str]) -> dict[str, list[dict]]:
    """Return the generated Item Prices of several properties by property.

    Args:
        properties: ``Utility Property`` names to group by.

    Returns:
        Mapping of property name to its ordered Item Price rows.
    """
    return {
        property_name: get_created_prices(property_name) for property_name in properties
    }


def build_schedule_html(
    properties: list[str],
    price_list: str | None = None,
    service_items: dict | None = None,
) -> str:
    """Render the generated Item Prices grouped by property as HTML.

    Args:
        properties: Properties to render.
        price_list: Optional price list filter.
        service_items: Mapping of property name to service item code, used to
            report properties that have no prices yet.

    Returns:
        HTML markup listing each property with its rent periods.
    """
    service_items = service_items or {}
    sections = [
        _render_property_section(
            property_name,
            get_created_prices(property_name, price_list),
            service_items,
        )
        for property_name in properties
    ]

    if not sections:
        return "<div class='text-muted'>No properties to show.</div>"

    return (
        "<div class='utility-item-price-summary'>"
        + "".join(sections)
        + "</div>"
        + _PRICE_SUMMARY_STYLES
    )


def _render_property_section(
    property_name: str, prices: list[dict], service_items: dict
) -> str:
    """Render one property block of the summary."""
    item_code = service_items.get(property_name)
    header = (
        "<div class='uips-property'>"
        f"<span class='uips-name'>{frappe.utils.escape_html(property_name)}</span>"
    )
    if item_code:
        header += f"<span class='uips-item'>{frappe.utils.escape_html(item_code)}</span>"

    header += f"<span class='uips-count'>{len(prices)} period(s)</span></div>"

    if not prices:
        return (
            header
            + "<div class='uips-empty text-muted'>No Item Prices created yet.</div>"
        )

    rows = "".join(_render_price_row(price) for price in prices)

    return (
        header
        + "<table class='table table-bordered uips-table'><thead><tr>"
        + "<th>From</th><th>To</th><th>Item</th><th>Customer</th>"
        + "<th class='text-right'>Rate</th>"
        + f"</tr></thead><tbody>{rows}</tbody></table>"
    )


def _render_price_row(price: dict) -> str:
    """Render a single Item Price row."""
    valid_upto = (
        frappe.utils.formatdate(price.valid_upto) if price.valid_upto else _("Open ended")
    )

    return (
        "<tr>"
        f"<td>{frappe.utils.formatdate(price.valid_from)}</td>"
        f"<td>{valid_upto}</td>"
        f"<td>{frappe.utils.escape_html(price.item_code or '')}</td>"
        f"<td>{frappe.utils.escape_html(price.customer or '')}</td>"
        f"<td class='text-right'>{frappe.utils.fmt_money(price.price_list_rate)}</td>"
        "</tr>"
    )


_PRICE_SUMMARY_STYLES = """
<style>
.utility-item-price-summary .uips-property {
    display: flex;
    align-items: baseline;
    gap: 8px;
    margin: 12px 0 4px;
    font-weight: 600;
}
.utility-item-price-summary .uips-item,
.utility-item-price-summary .uips-count {
    font-weight: 400;
    font-size: 12px;
    color: var(--text-muted);
}
.utility-item-price-summary .uips-table { margin-bottom: 4px; }
.utility-item-price-summary .uips-table td,
.utility-item-price-summary .uips-table th { padding: 4px 8px; }
.utility-item-price-summary .uips-empty { margin-bottom: 8px; }
</style>
"""
