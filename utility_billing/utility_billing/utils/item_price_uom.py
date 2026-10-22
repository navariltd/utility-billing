"""UOM resolution for generated Item Prices.

``Item Price`` rejects a UOM that is not available on the item, so the UOM
configured in Utility Billing Settings is only trusted after it has been
verified against the items actually being priced.
"""

import frappe
from frappe import _

FALLBACK_UOM = "Nos"


def resolve_uom(settings, item_codes: list[str]) -> str:
    """Return the UOM to use for the generated Item Prices.

    Args:
        settings: ``Utility Billing Settings`` document.
        item_codes: Items the Item Prices will be created for.

    Returns:
        A UOM valid for every item being priced.

    Raises:
        frappe.ValidationError: When no valid UOM can be determined.
    """
    configured = settings.default_item_price_uom
    if configured and uom_valid_for_all(configured, item_codes):
        return configured

    return _stock_uom(item_codes) or _configured_fallback(configured) or _record_fallback()


def uom_valid_for_all(uom: str, item_codes: list[str]) -> bool:
    """Return whether ``uom`` is available on every item.

    Args:
        uom: UOM name to check.
        item_codes: Items the UOM must be valid for.

    Returns:
        ``True`` when the UOM is the stock UOM of, or converted on, every item.
    """
    if not uom_exists(uom):
        return False

    for item_code in item_codes:
        if frappe.get_cached_value("Item", item_code, "stock_uom") == uom:
            continue

        if frappe.db.exists(
            "UOM Conversion Detail",
            {"parenttype": "Item", "parent": item_code, "uom": uom},
        ):
            continue

        return False

    return True


def uom_exists(uom: str) -> bool:
    """Return whether the UOM exists.

    Args:
        uom: UOM name to check.

    Returns:
        ``True`` when the UOM record exists or is the built in fallback.
    """
    if uom == FALLBACK_UOM:
        return True

    return bool(frappe.db.exists("UOM", uom))


def _stock_uom(item_codes: list[str]) -> str | None:
    """Return the shared stock UOM of every item, when there is exactly one."""
    stock_uoms = {
        frappe.get_cached_value("Item", item_code, "stock_uom") for item_code in item_codes
    }

    if len(stock_uoms) == 1 and None not in stock_uoms:
        return stock_uoms.pop()

    return None


def _configured_fallback(configured: str | None) -> str | None:
    """Return the configured UOM when it at least exists as a record."""
    if configured and uom_exists(configured):
        return configured

    return None


def _record_fallback() -> str | None:
    """Return any existing UOM usable as a last resort."""
    if uom_exists(FALLBACK_UOM):
        return FALLBACK_UOM

    existing = frappe.db.get_value("UOM", {}, "name")
    if existing:
        return existing

    frappe.throw(
        _(
            "Could not determine a UOM for the generated Item Prices. Please set "
            "the Item Price UOM in Utility Billing Settings to a UOM valid for "
            "the property service items."
        )
    )
