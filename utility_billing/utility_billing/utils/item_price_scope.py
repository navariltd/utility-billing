"""Scope checks shared by the Item Price schedule actions.

Every write made on behalf of a ``Utility Service Request`` has to be limited to
the service items of that request's own properties. These helpers resolve that
scope, re-check submitted record names against it and read back the contract
period recorded for a property.

Keeping the scope rules in one place means the modal actions and the summary
editor can never drift apart on which records they are allowed to touch.
"""

import frappe

from utility_billing.utility_billing.utils import item_price_summary

ITEM_PRICE_APPROACH = "Item Price"


def is_item_price_approach() -> bool:
    """Return whether the site bills rent by ``Item Price``.

    Hand edited schedules are only meaningful for that approach, so the editor
    is offered and saved only when this is ``True``.

    Returns:
        ``True`` when recurring rent is billed at the Item Price valid on the
        billing date.
    """
    approach = frappe.db.get_single_value(
        "Utility Billing Settings", "rent_billing_approach"
    )

    return approach == ITEM_PRICE_APPROACH


def request_service_items(service_request) -> set[str]:
    """Return the item codes the request's properties are billed with.

    Args:
        service_request: ``Utility Service Request`` document.

    Returns:
        Item codes whose prices belong to this request.
    """
    properties = [
        row.utility_property
        for row in service_request.requested_properties
        if row.utility_property
    ]

    return set(item_price_summary.get_property_item_codes(properties))


def property_item_code(service_request, property_name: str) -> str | None:
    """Return the service item of a property.

    Args:
        service_request: ``Utility Service Request`` document.
        property_name: ``Utility Property`` name.

    Returns:
        The property's service item code, or ``None`` when it has none.
    """
    for item_code, name in item_price_summary.get_property_item_codes(
        [property_name]
    ).items():
        if name == property_name:
            return item_code

    return None


def property_contract_period(service_request, property_name: str) -> tuple:
    """Return the contract period recorded for a property.

    The requested property row holds the dates of that property's own contract;
    the document level dates are only a fallback for rows without them.

    Args:
        service_request: ``Utility Service Request`` document.
        property_name: ``Utility Property`` name.

    Returns:
        ``(start_date, end_date)`` of the property's contract.
    """
    for row in service_request.requested_properties:
        if row.utility_property == property_name:
            return (
                row.start_date or service_request.start_date,
                row.end_date or service_request.end_date,
            )

    return service_request.start_date, service_request.end_date


def get_allowed_price(name: str, allowed_items: set[str]):
    """Return an Item Price only when it belongs to an allowed item.

    Args:
        name: ``Item Price`` name submitted by the client.
        allowed_items: Item codes this request is allowed to edit.

    Returns:
        The ``Item Price`` row, or ``None`` when it is out of scope.
    """
    if not name or not allowed_items:
        return None

    return frappe.db.get_value(
        "Item Price",
        {"name": name, "item_code": ("in", list(allowed_items))},
        [
            "name",
            "item_code",
            "price_list",
            "price_list_rate",
            "valid_from",
            "valid_upto",
            "customer",
        ],
        as_dict=True,
    )
