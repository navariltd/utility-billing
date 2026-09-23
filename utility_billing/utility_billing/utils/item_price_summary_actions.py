"""Apply manually edited Item Price schedules from the request summary.

The Item Price Summary field shows the real ``Item Price`` records of every
property. Editing it - changing a date or a rate, adding a period or dropping
one - is a manual override of the generated schedule, so it is only allowed when
the site bills rent by ``Item Price``.

The whole schedule of a property is validated before anything is written: it has
to cover the contract period without gaps or overlaps, so a partial manual edit
can never silently leave a stretch of the contract unpriced.
"""

import frappe
from frappe import _
from frappe.utils import flt, getdate

from utility_billing.utility_billing.utils import item_price_scope as scope
from utility_billing.utility_billing.utils import item_price_uom
from utility_billing.utility_billing.utils import item_prices as item_price_utils
from utility_billing.utility_billing.utils.item_price_schedule import RatePeriod
from utility_billing.utility_billing.utils.item_price_validation import (
    build_manual_schedule,
)
from utility_billing.utility_billing.utils.price_list import resolve_price_list


@frappe.whitelist()
def save_item_price_schedule(docname: str, schedules: dict | str) -> dict:
    """Apply the edited schedule of every submitted property.

    Args:
        docname: ``Utility Service Request`` name.
        schedules: Mapping of property name to
            ``{"periods": [{"name", "valid_from", "valid_upto",
            "price_list_rate", "customer"}], "deleted": [<Item Price name>]}``.

    Returns:
        Counts of updated, created, deleted, unchanged and skipped rows.

    Raises:
        frappe.ValidationError: When rent is not billed by ``Item Price``, a
            period is incomplete or the schedule does not cover the contract
            period of the property.
    """
    _require_item_price_approach()

    service_request = frappe.get_doc("Utility Service Request", docname)
    service_request.check_permission("write")

    result = {"updated": 0, "created": 0, "deleted": 0, "unchanged": 0, "skipped": 0}

    for property_name, schedule in _parse_schedules(schedules).items():
        _apply_property_schedule(service_request, property_name, schedule, result)

    return result


def _require_item_price_approach() -> None:
    """Raise when the site does not bill rent by ``Item Price``."""
    if not scope.is_item_price_approach():
        frappe.throw(
            _(
                "Manual schedule editing is only available when rent is billed "
                "by Item Price."
            )
        )


def _parse_schedules(schedules) -> dict:
    """Return the submitted schedules as a mapping of property to schedule."""
    parsed = frappe.parse_json(schedules) if isinstance(schedules, str) else schedules

    return {
        name: value
        for name, value in (parsed or {}).items()
        if isinstance(value, dict)
    }


def _apply_property_schedule(service_request, property_name, schedule, result) -> None:
    """Validate and save the edited schedule of one property."""
    if property_name not in _requested_properties(service_request):
        frappe.throw(
            _("Property {0} is not part of this request.").format(property_name)
        )

    item_code = scope.property_item_code(service_request, property_name)
    if not item_code:
        frappe.throw(
            _("Property {0} has no service item to price.").format(property_name)
        )

    allowed_items = {item_code}
    start_date, end_date = scope.property_contract_period(service_request, property_name)

    rows = [row for row in (schedule.get("periods") or []) if isinstance(row, dict)]
    deleted = [name for name in (schedule.get("deleted") or []) if name]

    _reject_conflicting_names(rows, deleted)

    for group_rows in _group_by_customer(rows).values():
        _validate_group(property_name, group_rows, start_date, end_date)

    for name in deleted:
        _delete_price(name, allowed_items, result)

    options = _build_options(service_request, item_code, start_date, end_date)

    # Updates run before inserts so a split period frees its dates for the new
    # row instead of being seen as an overlap.
    for row in rows:
        if row.get("name"):
            _update_price(row, allowed_items, result)

    for row in rows:
        if not row.get("name"):
            _create_price(
                options,
                row,
                item_code,
                property_name,
                row.get("customer") or service_request.customer,
                result,
            )


def _requested_properties(service_request) -> set[str]:
    """Return the properties requested on the service request."""
    return {
        row.utility_property
        for row in service_request.requested_properties
        if row.utility_property
    }


def _reject_conflicting_names(rows: list[dict], deleted: list[str]) -> None:
    """Raise when a period is submitted as both kept and removed."""
    submitted = {row["name"] for row in rows if row.get("name")}

    if submitted & set(deleted):
        frappe.throw(_("A rent period cannot be both kept and removed."))


def _group_by_customer(rows: list[dict]) -> dict:
    """Group the submitted periods by the customer they are scoped to.

    A blank customer is a price that applies to every customer, so it forms its
    own group rather than being folded into the request's customer.
    """
    groups = {}

    for row in rows:
        groups.setdefault(row.get("customer") or None, []).append(row)

    return groups


def _validate_group(
    property_name: str, rows: list[dict], start_date, end_date
) -> None:
    """Raise when a customer's periods do not cover the contract period."""
    periods = [_to_period(row) for row in rows]

    try:
        build_manual_schedule(periods, start_date, end_date)
    except ValueError as error:
        frappe.throw(_("{0}: {1}").format(property_name, str(error)))


def _to_period(row: dict) -> RatePeriod:
    """Return a submitted period as a ``RatePeriod``.

    Raises:
        frappe.ValidationError: If the period is missing a date.
    """
    valid_from = row.get("valid_from")
    valid_upto = row.get("valid_upto")

    if not valid_from or not valid_upto:
        frappe.throw(_("Every rent period needs a From and a To date."))

    return RatePeriod(
        valid_from=getdate(valid_from),
        valid_upto=getdate(valid_upto),
        rate=flt(row.get("price_list_rate")),
        increment_count=0,
    )


def _build_options(
    service_request, item_code: str, start_date, end_date
) -> item_price_utils.ScheduleOptions:
    """Return the options needed to insert a new Item Price."""
    settings = frappe.get_cached_doc("Utility Billing Settings")
    price_list = service_request.price_list or resolve_price_list(
        service_request.customer
    )

    if not price_list:
        frappe.throw(_("Please set a Price List before editing Item Prices."))

    return item_price_utils.ScheduleOptions(
        price_list=price_list,
        start_date=start_date,
        end_date=end_date,
        uom=item_price_uom.resolve_uom(settings, [item_code]),
    )


def _delete_price(name: str, allowed_items: set[str], result: dict) -> None:
    """Delete the Item Price of ``name`` when it belongs to the request."""
    price = scope.get_allowed_price(name, allowed_items)
    if not price:
        result["skipped"] += 1
        return

    frappe.delete_doc("Item Price", price.name, ignore_permissions=True, force=True)
    result["deleted"] += 1


def _update_price(row: dict, allowed_items: set[str], result: dict) -> None:
    """Write the new dates and rate of an existing Item Price."""
    price = scope.get_allowed_price(row.get("name"), allowed_items)
    if not price:
        result["skipped"] += 1
        return

    valid_from = getdate(row.get("valid_from"))
    valid_upto = getdate(row.get("valid_upto"))
    rate = flt(row.get("price_list_rate"))

    if (
        getdate(price.valid_from) == valid_from
        and getdate(price.valid_upto) == valid_upto
        and flt(price.price_list_rate) == rate
    ):
        result["unchanged"] += 1
        return

    frappe.db.set_value(
        "Item Price",
        price.name,
        {"price_list_rate": rate, "valid_from": valid_from, "valid_upto": valid_upto},
        update_modified=False,
    )
    result["updated"] += 1


def _create_price(
    options: item_price_utils.ScheduleOptions,
    row: dict,
    item_code: str,
    property_name: str,
    customer: str | None,
    result: dict,
) -> None:
    """Insert an Item Price for a newly added period."""
    period = _to_period(row)
    line = item_price_utils.ScheduleLine(
        item_code=item_code,
        customer=customer or None,
        base_rate=period.rate,
        utility_property=property_name,
    )

    if item_price_utils.has_overlapping_price(options, line, period):
        result["skipped"] += 1
        return

    item_price_utils.insert_item_price(options, line, period)
    result["created"] += 1
