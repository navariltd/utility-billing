"""Item Price schedule actions of the Utility Service Request.

Exposes the ``Define Item Prices`` action: a preview of the rates generated
from a lease period and an increment rule, and the creation of the matching
``Item Price`` records for the property service item and the tenant customer.
"""

import frappe
from frappe.utils import cint

from utility_billing.utility_billing.utils import item_prices as item_price_utils
from utility_billing.utility_billing.utils import item_price_schedule_helpers as helpers
from utility_billing.utility_billing.utils import item_price_summary


@frappe.whitelist()
def get_item_price_summary(docname: str) -> dict:
    """Return the HTML summary of the Item Prices created for a request.

    Args:
        docname: ``Utility Service Request`` name.

    Returns:
        Dictionary holding the rendered HTML and whether any prices exist.
    """
    service_request = frappe.get_doc("Utility Service Request", docname)
    service_request.check_permission("read")

    properties = [
        row.utility_property
        for row in service_request.requested_properties
        if row.utility_property
    ]
    service_items = helpers.resolve_service_items(properties) if properties else {}
    html = item_price_summary.build_schedule_html(
        properties, service_request.price_list, service_items
    )
    has_prices = any(
        item_price_summary.get_created_prices(property_name, service_request.price_list)
        for property_name in properties
    )

    return {"html": html, "has_prices": has_prices}


@frappe.whitelist()
def preview_item_price_schedule(
    docname: str,
    properties: list | str,
    base_rates: dict | str,
    start_date: str,
    end_date: str = None,
    price_list: str = None,
    customer: str = None,
    adjustment_rule: str = None,
    overrides: list | str = None,
    frequency: str = None,
    increment: dict | str = None,
) -> list[dict]:
    """Return the rate periods that a schedule would create.

    Args:
        docname: ``Utility Service Request`` name.
        properties: Properties being scheduled.
        base_rates: Mapping of property name to its first period rent.
        start_date: Lease start date.
        end_date: Lease end date, optional for open ended leases.
        price_list: Price list for the generated Item Prices.
        customer: Customer the Item Prices are scoped to.
        adjustment_rule: Optional ``Billing Adjustment Rule`` supplying defaults.
        overrides: Optional manual rate periods.
        frequency: Optional manual billing frequency.
        increment: Optional manual increment settings.

    Returns:
        One entry per property holding the generated rate periods.
    """
    service_request = frappe.get_doc("Utility Service Request", docname)
    service_request.check_permission("read")

    service_items = helpers.resolve_service_items(helpers.as_list(properties))
    options = helpers.build_options(
        price_list or service_request.price_list,
        start_date,
        end_date,
        adjustment_rule,
        service_items=service_items,
        frequency=frequency,
        increment=helpers.parse_increment(increment),
    )
    options.overrides = helpers.parse_overrides(overrides)

    lines = helpers.build_lines(
        service_items, customer or service_request.customer, helpers.as_dict(base_rates)
    )

    preview = item_price_utils.preview_schedule(options, lines)
    for entry, property_name in zip(preview, service_items.keys()):
        entry["property"] = property_name
        entry["periods"] = [helpers.serialize_period(period) for period in entry["periods"]]

    return preview


@frappe.whitelist()
def create_item_price_schedule(
    docname: str,
    properties: list | str,
    base_rates: dict | str,
    start_date: str,
    end_date: str = None,
    price_list: str = None,
    customer: str = None,
    adjustment_rule: str = None,
    overrides: list | str = None,
    replace_existing: int = 0,
    frequency: str = None,
    increment: dict | str = None,
) -> dict:
    """Create the Item Prices of a property rent schedule.

    Re-running the action skips periods that already have a matching Item
    Price, so the same schedule can be submitted twice without duplicates.

    Args:
        docname: ``Utility Service Request`` name.
        properties: Properties being scheduled.
        base_rates: Mapping of property name to its first period rent.
        start_date: Lease start date.
        end_date: Lease end date, optional for open ended leases.
        price_list: Price list for the generated Item Prices.
        customer: Customer the Item Prices are scoped to.
        adjustment_rule: Optional ``Billing Adjustment Rule`` supplying defaults.
        overrides: Optional manual rate periods.
        replace_existing: When set, previously generated schedule prices of
            the same item and customer are removed first.
        frequency: Optional manual billing frequency.
        increment: Optional manual increment settings.

    Returns:
        Counts of created and skipped Item Prices plus the stored schedule.
    """
    service_request = frappe.get_doc("Utility Service Request", docname)
    service_request.check_permission("write")

    resolved_customer = customer or service_request.customer
    service_items = helpers.resolve_service_items(helpers.as_list(properties))
    options = helpers.build_options(
        price_list or service_request.price_list,
        start_date,
        end_date,
        adjustment_rule,
        service_items=service_items,
        frequency=frequency,
        increment=helpers.parse_increment(increment),
        require_price_list=True,
    )
    options.overrides = helpers.parse_overrides(overrides)

    if cint(replace_existing):
        for item_code in service_items.values():
            item_price_utils.delete_existing_schedule(
                item_code, options.price_list, resolved_customer
            )

    lines = helpers.build_lines(service_items, resolved_customer, helpers.as_dict(base_rates))
    result = item_price_utils.create_item_prices(options, lines)

    schedule_rows = item_price_utils.preview_schedule(options, lines)
    schedule_rows = _annotate_schedule(schedule_rows, service_items)

    return {
        "created_count": result["created_count"],
        "skipped": result["skipped"],
        "schedule": schedule_rows,
    }


def _annotate_schedule(
    schedule_rows: list[dict], service_items: dict[str, str]
) -> list[dict]:
    """Add the source property of each schedule entry.

    ``preview_schedule`` groups rows by item only, so the property that owns
    each entry is added here. This keeps the create response shaped exactly
    like the preview response.

    Args:
        schedule_rows: Entries returned by ``preview_schedule``.
        service_items: Mapping of property name to service item code.

    Returns:
        The same entries, each carrying its ``property``.
    """
    properties_by_item = {
        item_code: property_name for property_name, item_code in service_items.items()
    }

    for entry in schedule_rows:
        entry["property"] = properties_by_item.get(entry["item_code"])

    return schedule_rows
