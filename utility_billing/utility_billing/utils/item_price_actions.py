"""Item Price schedule actions of the Utility Service Request.

Exposes the ``Define Item Prices`` action: a preview of the rates generated
from a lease period and an increment rule, the creation of the matching
``Item Price`` records for the property service item and the tenant customer,
and the manual correction of rates on already created records.
"""

import frappe
from frappe import _
from frappe.utils import cint, flt

from utility_billing.utility_billing.utils import item_prices as item_price_utils
from utility_billing.utility_billing.utils import item_price_schedule_helpers as helpers
from utility_billing.utility_billing.utils import item_price_scope as scope
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
    property_periods = {
        row.utility_property: (row.start_date, row.end_date)
        for row in service_request.requested_properties
        if row.utility_property
    }

    html = item_price_summary.build_schedule_html(
        properties,
        service_request.price_list,
        property_periods=property_periods,
        customer=service_request.customer,
        editable=scope.is_item_price_approach(),
    )

    item_by_property = {
        property_name: item_code
        for item_code, property_name in item_price_summary.get_property_item_codes(
            properties
        ).items()
    }
    has_prices = any(
        item_price_summary.get_created_prices(item_code, service_request.price_list)
        for item_code in item_by_property.values()
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
    manual_schedules: dict | str = None,
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
        manual_schedules: Optional hand edited periods per property, replacing
            generation for those properties.

    Returns:
        One entry per property holding the generated rate periods.

    Raises:
        frappe.ValidationError: If the inputs are incomplete or a manual
            schedule does not cover the property's contract period.
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
        customer=customer or service_request.customer,
    )
    options.overrides = helpers.parse_overrides(overrides)

    lines = helpers.build_lines(
        service_items,
        customer or service_request.customer,
        helpers.as_dict(base_rates),
        helpers.parse_manual_schedules(manual_schedules),
    )

    try:
        preview = item_price_utils.preview_schedule(options, lines)
    except ValueError as error:
        frappe.throw(str(error))

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
    manual_schedules: dict | str = None,
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
        manual_schedules: Optional hand edited periods per property, replacing
            generation for those properties.

    Returns:
        Counts of created and skipped Item Prices plus the stored schedule.

    Raises:
        frappe.ValidationError: If the inputs are incomplete or a manual
            schedule does not cover the property's contract period.
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
        customer=resolved_customer,
    )
    options.overrides = helpers.parse_overrides(overrides)

    lines = helpers.build_lines(
        service_items,
        resolved_customer,
        helpers.as_dict(base_rates),
        helpers.parse_manual_schedules(manual_schedules),
    )

    try:
        if cint(replace_existing):
            for item_code in service_items.values():
                item_price_utils.delete_existing_schedule(
                    item_code, options.price_list, resolved_customer
                )

        result = item_price_utils.create_item_prices(options, lines)
        schedule_rows = item_price_utils.preview_schedule(options, lines)
    except ValueError as error:
        frappe.throw(str(error))

    schedule_rows = _annotate_schedule(schedule_rows, service_items)

    return {
        "created_count": result["created_count"],
        "skipped": result["skipped"],
        "schedule": schedule_rows,
    }


@frappe.whitelist()
def update_item_price_rates(docname: str, rates: list | str) -> dict:
    """Apply manual rate corrections to the Item Prices of a request.

    Only ``price_list_rate`` is updated - dates and scope are left alone, so an
    edit can never move a period or re-point a price at another item. Each
    submitted name is re-validated against the request's own properties before
    it is written, so a name from elsewhere cannot be edited through this call.

    Args:
        docname: ``Utility Service Request`` name.
        rates: Rows of ``{"name": <Item Price>, "price_list_rate": <number>}``.

    Returns:
        Counts of updated rows, values skipped as unchanged, and rows rejected
        because they do not belong to the request.

    Raises:
        frappe.ValidationError: If a rate is not a non-negative number.
    """
    service_request = frappe.get_doc("Utility Service Request", docname)
    service_request.check_permission("write")

    allowed_items = scope.request_service_items(service_request)
    updated = 0
    unchanged = 0
    rejected = 0

    for row in _parse_rate_rows(rates):
        rate = flt(row.get("price_list_rate"))
        if rate < 0:
            frappe.throw(_("Item Price rates cannot be negative."))

        price = scope.get_allowed_price(row.get("name"), allowed_items)
        if not price:
            rejected += 1
            continue

        if flt(price.price_list_rate) == rate:
            unchanged += 1
            continue

        frappe.db.set_value(
            "Item Price", price.name, "price_list_rate", rate, update_modified=False
        )
        updated += 1

    return {"updated": updated, "unchanged": unchanged, "rejected": rejected}


def _parse_rate_rows(rates: list | str) -> list[dict]:
    """Coerce the submitted rate rows into a list of dicts.

    Args:
        rates: JSON string or list of rate rows.

    Returns:
        The rate rows as a list.
    """
    parsed = helpers.as_list(rates)

    return [row for row in parsed if isinstance(row, dict) and row.get("name")]


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
