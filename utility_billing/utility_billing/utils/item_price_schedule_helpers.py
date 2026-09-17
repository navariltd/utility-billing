"""Shared helpers for the Item Price schedule actions.

Builds the schedule lines, options and response payloads used by
``utility_billing.utility_billing.utils.item_price_actions``. Kept separate so
the whitelisted action module stays focused on request handling.
"""

from dataclasses import asdict
from typing import Any

import frappe
from frappe import _
from frappe.utils import cstr, flt, getdate

from utility_billing.utility_billing.utils import item_prices as item_price_utils
from utility_billing.utility_billing.utils import item_price_uom
from utility_billing.utility_billing.utils.item_price_schedule import RateOverride
from utility_billing.utility_billing.utils.service_item import ensure_service_item


def resolve_service_items(properties: list[str]) -> dict[str, str]:
    """Return the rent billing service item of every property.

    Args:
        properties: ``Utility Property`` names.

    Returns:
        Mapping of property name to service item code.

    Raises:
        frappe.ValidationError: If a property has no service item and auto
            creation is disabled.
    """
    items = {}

    for property_name in properties:
        item_code = ensure_service_item(property_name)
        if not item_code:
            frappe.throw(
                _(
                    "Property {0} has no service item. Enable auto creation of "
                    "property service items in Utility Billing Settings or set "
                    "the item manually."
                ).format(property_name)
            )
        items[property_name] = item_code

    return items


def build_options(
    price_list: str | None,
    start_date: str,
    end_date: str,
    adjustment_rule: str | None,
    service_items: dict[str, str] | None = None,
    frequency: str | None = None,
    increment: dict | None = None,
    require_price_list: bool = False,
) -> item_price_utils.ScheduleOptions:
    """Build the shared schedule options of a request.

    The billing frequency and the increment parameters are taken from the
    ``Billing Adjustment Rule`` unless the user supplied values manually.

    Args:
        price_list: Price list the Item Prices are created in.
        start_date: Lease start date.
        end_date: Lease end date.
        adjustment_rule: Optional ``Billing Adjustment Rule`` supplying defaults.
        service_items: Mapping of property name to service item code, used to
            resolve a UOM valid for the items being priced.
        frequency: Manual billing frequency override.
        increment: Manual increment values, see ``parse_increment``.
        require_price_list: Whether a price list must be set. Previewing a
            schedule does not need one, creating Item Prices does.

    Returns:
        Options shared by every line of the schedule.

    Raises:
        frappe.ValidationError: If a required value is missing.
    """
    if require_price_list and not price_list:
        frappe.throw(_("Please set a Price List before creating Item Prices."))

    if not start_date:
        frappe.throw(_("Please set the lease Start Date before defining item prices."))

    settings = frappe.get_cached_doc("Utility Billing Settings")
    manual = increment or {}

    return item_price_utils.ScheduleOptions(
        price_list=price_list or "",
        start_date=start_date,
        end_date=end_date or None,
        uom=item_price_uom.resolve_uom(settings, list((service_items or {}).values())),
        frequency=frequency or item_price_utils.resolve_frequency(adjustment_rule),
        rule=item_price_utils.build_increment_rule(
            adjustment_rule,
            interval_months=manual.get("interval_months"),
            percentage=manual.get("percentage"),
            effective_after_months=manual.get("effective_after_months"),
            basis=manual.get("basis"),
        ),
    )


def parse_increment(increment: Any) -> dict:
    """Return the manual increment values supplied by the client.

    Args:
        increment: JSON object or dictionary with the increment fields. Blank
            values are dropped so the rule document keeps providing them.

    Returns:
        Dictionary holding only the values the user actually set.
    """
    if not increment:
        return {}

    parsed = parse_json(increment) or {}
    fields = (
        "interval_months",
        "percentage",
        "effective_after_months",
        "basis",
    )

    return {
        field: parsed[field]
        for field in fields
        if parsed.get(field) not in (None, "")
    }


def build_lines(
    service_items: dict[str, str], customer: str | None, base_rates: dict[str, float]
) -> list[item_price_utils.ScheduleLine]:
    """Build one schedule line per property service item.

    Args:
        service_items: Mapping of property name to service item code.
        customer: Customer the Item Prices are scoped to, if any.
        base_rates: Mapping of property name to the first period rate.

    Returns:
        Schedule lines for every property.

    Raises:
        frappe.ValidationError: If a property has no base rate.
    """
    lines = []

    for property_name, item_code in service_items.items():
        base_rate = base_rates.get(property_name)
        if base_rate is None:
            frappe.throw(
                _("Please enter the rent amount for property {0}.").format(property_name)
            )

        lines.append(
            item_price_utils.ScheduleLine(
                item_code=item_code,
                customer=customer or None,
                base_rate=flt(base_rate),
                utility_property=property_name,
            )
        )

    return lines


def parse_overrides(overrides: Any) -> list[RateOverride]:
    """Return the manual rate overrides supplied by the client.

    Args:
        overrides: JSON list or Python list of ``{from_date, rate}`` entries.

    Returns:
        Parsed overrides, ignoring incomplete entries.
    """
    result = []

    for override in parse_json(overrides) or []:
        if not override.get("from_date") or override.get("rate") is None:
            continue
        result.append(
            RateOverride(
                from_date=getdate(cstr(override["from_date"])), rate=flt(override["rate"])
            )
        )

    return result


def parse_json(value: Any):
    """Return ``value`` decoded from JSON when it is a string.

    Args:
        value: JSON encoded payload or an already decoded value.

    Returns:
        Decoded list, dictionary or the original value.
    """
    if isinstance(value, str):
        return frappe.parse_json(value)

    return value


def as_list(value: Any) -> list:
    """Return ``value`` as a list, parsing JSON strings."""
    return list(parse_json(value) or [])


def as_dict(value: Any) -> dict:
    """Return ``value`` as a dictionary, parsing JSON strings."""
    if value is None:
        return {}

    return dict(parse_json(value))


def serialize_period(period: Any) -> dict:
    """Return a JSON serialisable rate period.

    Args:
        period: ``RatePeriod`` instance or plain dictionary.

    Returns:
        Dictionary with string dates and float rates.
    """
    data = asdict(period) if hasattr(period, "__dataclass_fields__") else dict(period)
    data["valid_from"] = str(data["valid_from"])
    data["valid_upto"] = str(data["valid_upto"])
    data["rate"] = flt(data["rate"])

    return data
