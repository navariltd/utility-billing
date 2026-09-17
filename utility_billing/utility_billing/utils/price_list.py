"""Price list resolution for a Utility Service Request.

A request needs a price list so item rates and the rent schedule can resolve.
The value is taken from, in order:

1. the request itself, when one is already set;
2. the customer's ``default_price_list``;
3. the ``Default Price List`` configured in Utility Billing Settings.
"""

import frappe


def resolve_price_list(customer: str | None = None) -> str | None:
    """Return the price list to default a service request to.

    Args:
        customer: Customer the request belongs to, if any.

    Returns:
        The resolved price list, or ``None`` when none is configured.
    """
    if customer:
        customer_price_list = frappe.db.get_value(
            "Customer", customer, "default_price_list"
        )
        if customer_price_list:
            return customer_price_list

    return (
        frappe.db.get_single_value("Utility Billing Settings", "default_price_list")
        or None
    )


def apply_default_price_list(doc) -> None:
    """Set the price list on a service request when it has none.

    An explicitly chosen price list is never overwritten.

    Args:
        doc: ``Utility Service Request`` document.
    """
    if doc.get("price_list"):
        return

    price_list = resolve_price_list(doc.get("customer") or doc.get("party_name"))
    if price_list:
        doc.price_list = price_list
