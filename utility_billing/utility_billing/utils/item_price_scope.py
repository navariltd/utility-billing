"""Scope checks shared by the Item Price schedule actions.

Every write made on behalf of a ``Utility Service Request`` has to be limited to
the service items of that request's own properties. These helpers resolve that
scope, re-check submitted record names against it and read back the contract
period recorded for a property.

Keeping the scope rules in one place means the modal actions and the summary
editor can never drift apart on which records they are allowed to touch.
"""

import frappe
from frappe import _
from frappe.utils import getdate

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


def requested_property_row(service_request, property_name: str):
    """Return the Requested Properties row of a property, or ``None``.

    Args:
        service_request: ``Utility Service Request`` document.
        property_name: ``Utility Property`` name.
    """
    for row in service_request.requested_properties:
        if row.utility_property == property_name:
            return row

    return None


def require_requested_property(service_request, property_name: str) -> None:
    """Block scheduling a property that is not requested on the request.

    Raises:
        frappe.ValidationError: When the property is not on the request.
    """
    if not requested_property_row(service_request, property_name):
        frappe.throw(
            _("Property {0} is not part of this request.").format(property_name)
        )


def property_lease_end(service_request, property_name: str) -> tuple:
    """Return the effective lease end of a property and where it comes from.

    The property's Requested Properties row wins; the request's Contract End
    Date is the fallback - the same rule ``property_contract_period`` follows.

    Args:
        service_request: ``Utility Service Request`` document.
        property_name: ``Utility Property`` name.

    Returns:
        ``(end_date, source_label)``, or ``(None, None)`` when open ended.
    """
    row = requested_property_row(service_request, property_name)

    if row and row.end_date:
        return getdate(row.end_date), _(
            "End Date of {0} in Requested Properties (row {1})"
        ).format(property_name, row.idx)

    if service_request.end_date:
        return getdate(service_request.end_date), _("Contract End Date (Contract Details)")

    return None, None


def validate_schedule_start(service_request, property_name: str, start_date) -> None:
    """Block a schedule starting before the property's contract start.

    The contract start is the property's Requested Properties row, falling back
    to the request's Contract Start Date - the rule the rows themselves follow.

    Args:
        service_request: ``Utility Service Request`` document.
        property_name: ``Utility Property`` name.
        start_date: First date of the schedule.

    Raises:
        frappe.ValidationError: When ``start_date`` is before the contract start.
    """
    contract_start, _end = property_contract_period(service_request, property_name)
    if not (start_date and contract_start):
        return

    if getdate(start_date) < getdate(contract_start):
        frappe.throw(
            _(
                "Item Price start date '{0}' for property {1} cannot be before "
                "contract start date '{2}'."
            ).format(getdate(start_date), property_name, getdate(contract_start))
        )


def validate_schedule_end(service_request, property_name: str, schedule_end) -> None:
    """Block a Lease End that differs from the property's effective lease end.

    Only compared when both are set: a blank Lease End falls back to the lease
    end, and an open ended lease accepts any Lease End.

    Args:
        service_request: ``Utility Service Request`` document.
        property_name: ``Utility Property`` name.
        schedule_end: Lease End entered for the schedule, if any.

    Raises:
        frappe.ValidationError: Naming both dates and where the lease end comes from.
    """
    lease_end, source = property_lease_end(service_request, property_name)
    if not (schedule_end and lease_end) or getdate(schedule_end) == lease_end:
        return

    frappe.throw(
        _(
            "End dates for property {0} do not match: Lease End (Define Item Prices) "
            "is '{1}' but {2} is '{3}'. Clear the Lease End to use the lease end, or "
            "set it to '{3}'."
        ).format(property_name, getdate(schedule_end), source, lease_end)
    )


def resolve_schedule_end(service_request, property_names: list[str], schedule_end):
    """Return the date generation must stop at.

    The dialog's Lease End when set; otherwise the properties' effective lease
    end, so a blank Lease End never generates past a lease that has an end.
    Only a genuinely open ended lease is left open, which the generator caps at
    ``ScheduleRequest.max_periods`` periods.

    Known follow-up: once an open ended lease's capped periods run out,
    invoicing fails with "No Item Price found" - a future job could detect and
    extend running-low schedules.

    Args:
        service_request: ``Utility Service Request`` document.
        property_names: Properties being scheduled.
        schedule_end: Lease End entered for the schedule, if any.

    Returns:
        The end date to generate up to, or ``None`` when open ended.

    Raises:
        frappe.ValidationError: When the Lease End is blank and the properties
            end on different dates, so no single boundary applies.
    """
    if schedule_end:
        return schedule_end

    ends = {property_lease_end(service_request, name)[0] for name in property_names}
    if len(ends) > 1:
        frappe.throw(
            _(
                "Properties {0} end on different dates. Define their Item Prices one "
                "property at a time."
            ).format(", ".join(property_names))
        )

    end = next(iter(ends), None)

    return str(end) if end else None


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
