"""Creation and lookup of the rental service item of a property.

Every billable property owns a non-stock sales item used for rent billing.
The item is named after the property so that rent lines on Sales Orders and
Sales Invoices can be traced back to the property without extra lookups.
"""

import frappe
from frappe import _

DEFAULT_SERVICE_ITEM_GROUP = "Utility and Rental"
FALLBACK_UOM = "Nos"


def get_settings() -> frappe._dict:
    """Return the Utility Billing Settings cached as a dict."""
    return frappe.get_cached_doc("Utility Billing Settings")


def ensure_service_item(property_name: str, save: bool = True) -> str | None:
    """Return the service item of a property, creating it when missing.

    Args:
        property_name: ``Utility Property`` name.
        save: Whether the property should be saved when the item is resolved.

    Returns:
        The service item code, or ``None`` when auto creation is disabled and
        the property has no service item yet.
    """
    property_doc = frappe.get_doc("Utility Property", property_name)

    if property_doc.service_item and frappe.db.exists("Item", property_doc.service_item):
        return property_doc.service_item

    item_code = create_service_item_for_property(property_doc)
    if not item_code:
        return None

    if save:
        property_doc.db_set("service_item", item_code, update_modified=False)
    else:
        property_doc.service_item = item_code

    return item_code


def get_service_item_of_property(property_name: str) -> str | None:
    """Return the rent billing item of a property.

    The service item is created on demand when auto creation is enabled, so a
    property always has something to bill when the feature is configured.

    Args:
        property_name: ``Utility Property`` name.

    Returns:
        The service item code, or ``None`` when the property does not exist or
        has no service item and auto creation is disabled.
    """
    if not frappe.db.exists("Utility Property", property_name):
        return None

    return ensure_service_item(property_name)


def get_property_of_service_item(item_code: str) -> str | None:
    """Return the property billed through an item.

    Service items are created for billable properties only and are named after
    their property, so the item identifies the property it belongs to.

    Args:
        item_code: Item to resolve.

    Returns:
        The ``Utility Property`` name, or ``None`` when the item is not the
        service item of a property.
    """
    if not item_code:
        return None

    properties = frappe.db.get_all(
        "Utility Property",
        filters={"service_item": item_code},
        pluck="name",
        order_by="name asc",
        limit=1,
    )

    return properties[0] if properties else None


def create_service_item_for_property(property_doc) -> str | None:
    """Create (or link) the rental service item of a property.

    The item is a non-stock sales item named after the property. When an item
    with that name already exists it is linked instead of being created, so
    repeated calls stay idempotent.

    Args:
        property_doc: ``Utility Property`` document.

    Returns:
        The item code, or ``None`` when auto creation is disabled or the
        property has no name to derive the item code from.
    """
    settings = get_settings()
    if not settings.auto_create_service_item:
        return None

    if not property_doc.property_name:
        return None

    item_code = property_doc.property_name

    if frappe.db.exists("Item", item_code):
        return item_code

    item_group = (
        settings.default_service_item_group
        or property_doc.utility_category
        or DEFAULT_SERVICE_ITEM_GROUP
    )
    if not frappe.db.exists("Item Group", item_group):
        item_group = _resolve_fallback_item_group()

    item_doc = frappe.get_doc(
        {
            "doctype": "Item",
            "item_code": item_code,
            "item_name": item_code,
            "item_group": item_group,
            "is_stock_item": 0,
            "is_fixed_asset": 0,
            "is_sales_item": 1,
            "is_purchase_item": 0,
            "is_utility_item": 1,
            "stock_uom": property_doc.get("uom") or FALLBACK_UOM,
            "description": _("Rental billing item for property {0}").format(
                property_doc.name
            ),
            "disabled": 0,
        }
    )
    item_doc.flags.ignore_mandatory = True
    item_doc.insert(ignore_permissions=True, ignore_mandatory=True)

    return item_doc.name


def _resolve_fallback_item_group() -> str:
    """Return a leaf utility item group usable for service items.

    Raises:
        frappe.ValidationError: When no suitable item group exists.
    """
    for candidate in (DEFAULT_SERVICE_ITEM_GROUP, "All Item Groups", "Fixed Asset"):
        if frappe.db.exists("Item Group", candidate):
            return candidate

    item_group = frappe.db.get_value("Item Group", {"is_group": 0}, "name")
    if not item_group:
        frappe.throw(
            _("Please configure a default item group for property service items.")
        )

    return item_group
