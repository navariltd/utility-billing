"""Read-only summary of the Item Prices generated for a service request.

Item Prices are the source of truth for the rent schedule, so this module reads
them back and renders them grouped by property. It is used by the HTML field on
``Utility Service Request`` instead of storing a duplicate schedule table.

Grouping works off the property's **service item**: each property owns an item
named after it, so an Item Price is attributed to a property by its
``item_code``. No extra tagging on ``Item Price`` is required.

Rates are rendered as inputs so a period can be corrected by hand. Saving the
edits is an explicit action - the surrounding page reads the inputs and calls
``update_item_price_rates`` - so nothing is written while typing.
"""

import frappe
from frappe import _


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
) -> str:
    """Render the Item Prices of the given properties as HTML.

    Args:
        properties: Properties to render.
        price_list: Optional price list filter.

    Returns:
        HTML markup listing each property with its rent periods.
    """
    # `get_property_item_codes` returns item -> property; invert for lookup.
    item_by_property = {
        property_name: item_code
        for item_code, property_name in get_property_item_codes(properties).items()
    }

    sections = [
        _render_property_section(
            property_name,
            get_created_prices(item_by_property[property_name], price_list)
            if property_name in item_by_property
            else [],
        )
        for property_name in properties
    ]

    if not sections:
        return "<div class='text-muted'>No properties to show.</div>"

    has_prices = any("data-item-price=" in section for section in sections)

    return (
        "<div class='utility-item-price-summary'>"
        + (_PRICE_SUMMARY_TOOLBAR if has_prices else "")
        + "".join(sections)
        + "</div>"
        + _PRICE_SUMMARY_STYLES
    )


def _render_property_section(property_name: str, prices: list[dict]) -> str:
    """Render one property block of the summary."""
    item_code = prices[0]["item_code"] if prices else None
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
        + "<th>From</th><th>To</th><th>Customer</th>"
        + "<th class='text-right uips-rate-col'>Rate</th>"
        + f"</tr></thead><tbody>{rows}</tbody></table>"
    )


def _render_price_row(price: dict) -> str:
    """Render a single Item Price row with an editable rate.

    The Item Price name is carried on the input so the caller knows exactly
    which record to update; the server re-validates that the record belongs to
    this request before writing.
    """
    valid_upto = (
        frappe.utils.formatdate(price.valid_upto) if price.valid_upto else _("Open ended")
    )
    rate = flt_rate(price.price_list_rate)
    name = frappe.utils.escape_html(price["name"])

    return (
        "<tr>"
        f"<td>{frappe.utils.formatdate(price.valid_from)}</td>"
        f"<td>{valid_upto}</td>"
        f"<td>{frappe.utils.escape_html(price.customer or '')}</td>"
        "<td class='text-right uips-rate-col'>"
        f"<input type='number' step='0.01' min='0' class='form-control input-sm uips-rate'"
        f" data-item-price=\"{name}\" data-original=\"{rate}\" value=\"{rate}\">"
        "</td>"
        "</tr>"
    )


def flt_rate(value) -> str:
    """Format a stored rate for an ``input[type=number]`` value.

    Args:
        value: Stored ``price_list_rate``.

    Returns:
        The rate as a plain decimal string, so the browser can parse it.
    """
    return f"{frappe.utils.flt(value):.2f}"


_PRICE_SUMMARY_TOOLBAR = """
<div class="uips-toolbar">
    <button type="button" class="btn btn-xs btn-primary uips-update-btn" disabled>
        Update Prices
    </button>
    <span class="uips-dirty text-muted"></span>
</div>
"""

_PRICE_SUMMARY_STYLES = """
<style>
.utility-item-price-summary .uips-toolbar {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 8px;
}
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
.utility-item-price-summary .uips-rate-col { width: 140px; }
.utility-item-price-summary .uips-rate.changed {
    border-color: var(--yellow-400, #f0ad4e);
    background-color: rgba(240, 173, 78, 0.1);
}
</style>
"""
