"""HTML rendering of the Item Price Summary field.

Each property gets a small editable table of its rent periods: the From and To
dates and the rate are inputs, a period can be dropped and a new one added. The
surrounding page (``bind_item_price_summary_editor``) collects these inputs and
saves them through ``save_item_price_schedule``.

Rendering is kept apart from the Item Price reads in ``item_price_summary`` so
the reading logic stays testable without HTML.
"""

from frappe import _
from frappe.utils import escape_html, flt, formatdate


def render_schedule(sections: list[dict], editable: bool = True) -> str:
    """Render the item price summary of every property.

    Args:
        sections: One entry per property holding ``property``, ``item_code``,
            ``price_list``, ``customer``, ``start_date``, ``end_date`` and the
            ``prices`` rows to show.
        editable: Whether the periods may be edited. ``False`` renders a
            read-only view without the editor controls.

    Returns:
        HTML markup listing each property with its rent periods.
    """
    if not sections:
        return "<div class='text-muted'>No properties to show.</div>"

    has_schedule = editable and any(section.get("item_code") for section in sections)
    body = "".join(_render_property(section, editable) for section in sections)

    return (
        "<div class='utility-item-price-summary'>"
        + (_TOOLBAR if has_schedule else "")
        + body
        + _STYLES
        + "</div>"
    )


def _render_property(section: dict, editable: bool) -> str:
    """Render one property block with its periods.

    The whole block is wrapped so the page can scope the editable periods, the
    removal markers and the add-row button to a single property.

    Args:
        section: Property name, item, contract dates and the prices to show.
        editable: Whether the periods may be edited.
    """
    property_name = section["property"]
    item_code = section.get("item_code")
    prices = section.get("prices") or []

    block = (
        "<div class='uips-property'"
        f" data-property=\"{escape_html(property_name)}\""
        f" data-item-code=\"{escape_html(item_code or '')}\""
        f" data-price-list=\"{escape_html(section.get('price_list') or '')}\""
        f" data-customer=\"{escape_html(section.get('customer') or '')}\""
        f" data-start-date=\"{_as_date(section.get('start_date'))}\""
        f" data-end-date=\"{_as_date(section.get('end_date'))}\""
        " data-deleted='[]'>"
        "<div class='uips-property-header'>"
        f"<span class='uips-name'>{escape_html(property_name)}</span>"
    )
    if item_code:
        block += f"<span class='uips-item'>{escape_html(item_code)}</span>"

    block += f"<span class='uips-count'>{len(prices)} period(s)</span>"
    block += "</div>"

    if not item_code:
        return (
            block
            + "<div class='uips-empty text-muted'>No service item for this property.</div>"
            + "</div>"
        )

    rows = "".join(_render_row(price, editable) for price in prices)
    empty = (
        ""
        if prices
        else "<tr class='uips-empty-row'><td colspan='5' class='text-muted'>"
        + _("No Item Prices created yet.")
        + "</td></tr>"
    )
    action_header = "<th></th>" if editable else ""
    add_row = (
        "<div class='uips-add-period-wrap'>"
        "<button type='button' class='btn btn-xs btn-default uips-add-row'>"
        + _("Add period")
        + "</button></div>"
        if editable
        else ""
    )

    return (
        block
        + "<table class='table table-bordered uips-table'><thead><tr>"
        + "<th>From</th><th>To</th><th>Customer</th>"
        + "<th class='text-right uips-rate-col'>Rate</th>"
        + action_header
        + f"</tr></thead><tbody>{rows}{empty}</tbody></table>"
        + add_row
        + "</div>"
    )


def _render_row(price: dict, editable: bool) -> str:
    """Render a single period row.

    The customer is the one recorded on the Item Price, which may be blank for
    prices that apply to every customer. Newly added rows default to the
    property block's customer instead.

    Args:
        price: ``Item Price`` row to render.
        editable: Whether the dates and rate are rendered as inputs.
    """
    name = escape_html(price.get("name") or "")
    customer = price.get("customer") or ""

    if not editable:
        return (
            "<tr class='uips-row'>"
            f"<td>{_display_date(price.get('valid_from'))}</td>"
            f"<td>{_display_date(price.get('valid_upto'))}</td>"
            f"<td class='uips-customer'>{escape_html(customer)}</td>"
            f"<td class='text-right uips-rate-col'>{_rate(price.get('price_list_rate'))}</td>"
            "</tr>"
        )

    return (
        "<tr class='uips-row'"
        f" data-item-price=\"{name}\""
        f" data-customer=\"{escape_html(customer)}\">"
        f"<td><input type='date' class='form-control input-sm uips-input uips-from'"
        f" value=\"{_as_date(price.get('valid_from'))}\"></td>"
        f"<td><input type='date' class='form-control input-sm uips-input uips-upto'"
        f" value=\"{_as_date(price.get('valid_upto'))}\"></td>"
        f"<td class='uips-customer'>{escape_html(customer)}</td>"
        "<td class='text-right uips-rate-col'>"
        "<input type='number' step='0.01' min='0'"
        " class='form-control input-sm uips-input uips-rate'"
        f" value=\"{_rate(price.get('price_list_rate'))}\">"
        "</td>"
        "<td class='text-right'>"
        "<button type='button' class='btn btn-xs btn-link uips-remove-row'"
        f" title=\"{_('Remove period')}\"><i class='fa fa-times'></i></button>"
        "</td>"
        "</tr>"
    )


def _as_date(value) -> str:
    """Return a stored date as an ``input[type=date]`` value."""
    return str(value)[:10] if value else ""


def _display_date(value) -> str:
    """Return a stored date formatted for display."""
    return formatdate(value) if value else ""


def _rate(value) -> str:
    """Return a stored rate as a plain decimal string."""
    return f"{flt(value):.2f}"


_TOOLBAR = """
<div class="uips-toolbar">
    <button type="button" class="btn btn-xs btn-primary uips-update-btn" disabled>
        Save Schedule
    </button>
    <span class="uips-dirty text-muted"></span>
</div>
"""

_STYLES = """
<style>
.utility-item-price-summary .uips-toolbar {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 8px;
}
.utility-item-price-summary .uips-property { margin: 12px 0 4px; }
.utility-item-price-summary .uips-property-header {
    display: flex;
    align-items: center;
    gap: 8px;
    font-weight: 600;
}
.utility-item-price-summary .uips-item,
.utility-item-price-summary .uips-count {
    font-weight: 400;
    font-size: 12px;
    color: var(--text-muted);
}
.utility-item-price-summary .uips-add-period-wrap { margin: 4px 0 10px; }
.utility-item-price-summary .uips-table { margin-bottom: 4px; }
.utility-item-price-summary .uips-table td,
.utility-item-price-summary .uips-table th { padding: 4px 8px; }
.utility-item-price-summary .uips-empty { margin-bottom: 8px; }
.utility-item-price-summary .uips-rate-col { width: 140px; }
.utility-item-price-summary .uips-row.changed td { background-color: rgba(240, 173, 78, 0.1); }
</style>
"""
