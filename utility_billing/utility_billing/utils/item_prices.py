"""Persistence of generated Item Price schedules.

Turns the rate periods produced by
``utility_billing.utility_billing.utils.item_price_schedule`` into
``Item Price`` records scoped to an item, a price list and optionally a
customer. Existing records overlapping a generated period are skipped so the
operation can be re-run safely.
"""

from dataclasses import dataclass
from typing import Any

import frappe
from frappe.utils import flt, getdate

from utility_billing.utility_billing.utils.item_price_schedule import (
    DEFAULT_ADJUSTMENT_BASIS,
    IncrementRule,
    RatePeriod,
    RateOverride,
    ScheduleRequest,
    build_schedule,
)


@dataclass
class ScheduleLine:
    """Input of a single item and customer combination to schedule.

    Attributes:
        item_code: Service item the prices are created for.
        customer: Customer the prices are scoped to, if any.
        base_rate: Rate of the first period.
        utility_property: Property the prices belong to, tagged onto every
            generated ``Item Price`` so prices can be grouped by property.
    """

    item_code: str
    customer: str | None
    base_rate: float
    utility_property: str | None = None


@dataclass
class ScheduleOptions:
    """Options shared by every line of a schedule request."""

    price_list: str
    start_date: str
    end_date: str | None
    uom: str
    frequency: str = "Monthly"
    rule: IncrementRule | None = None
    overrides: list[RateOverride] | None = None

    def to_request(self, line: ScheduleLine) -> ScheduleRequest:
        """Build the pure schedule request of ``line``.

        Args:
            line: Item and customer combination being scheduled.

        Returns:
            Schedule request for the line, using the effective increment rule.
        """
        return ScheduleRequest(
            start_date=getdate(self.start_date),
            end_date=getdate(self.end_date) if self.end_date else None,
            base_rate=flt(line.base_rate),
            frequency=self.frequency,
            rule=self.rule or IncrementRule(),
            overrides=list(self.overrides or []),
        )


def resolve_increment_rule(adjustment_rule: str | None) -> IncrementRule:
    """Build an increment rule from a ``Billing Adjustment Rule``.

    Args:
        adjustment_rule: Name of the rule, or ``None`` for no increments.

    Returns:
        Increment rule describing the schedule increments.
    """
    if not adjustment_rule:
        return IncrementRule()

    rule_doc = frappe.get_cached_doc("Billing Adjustment Rule", adjustment_rule)

    return IncrementRule(
        interval_months=flt(rule_doc.increment_interval_months),
        percentage=flt(rule_doc.increment_percentage),
        effective_after_months=flt(rule_doc.effective_after_months),
        basis=rule_doc.get("adjustment_basis") or DEFAULT_ADJUSTMENT_BASIS,
    )


def build_increment_rule(
    adjustment_rule: str | None,
    interval_months: Any = None,
    percentage: Any = None,
    effective_after_months: Any = None,
    basis: str | None = None,
) -> IncrementRule:
    """Build an increment rule from a rule document and manual values.

    Values supplied by the user override the ones taken from the
    ``Billing Adjustment Rule``, which allows a schedule to be tuned without
    changing the shared rule.

    Args:
        adjustment_rule: Name of the ``Billing Adjustment Rule`` supplying
            defaults, or ``None``.
        interval_months: Manual increment interval in months.
        percentage: Manual increment percentage.
        effective_after_months: Manual grace period before the first increment.
        basis: Manual adjustment basis.

    Returns:
        Increment rule holding the effective values.
    """
    rule = resolve_increment_rule(adjustment_rule)

    if interval_months not in (None, ""):
        rule.interval_months = flt(interval_months)
    if percentage not in (None, ""):
        rule.percentage = flt(percentage)
    if effective_after_months not in (None, ""):
        rule.effective_after_months = flt(effective_after_months)
    if basis:
        rule.basis = basis

    return rule


def resolve_frequency(adjustment_rule: str | None) -> str:
    """Return the billing frequency of an adjustment rule.

    Args:
        adjustment_rule: Name of the rule, or ``None`` for monthly billing.

    Returns:
        Frequency used to build schedule periods.
    """
    if not adjustment_rule:
        return "Monthly"

    return frappe.get_cached_value(
        "Billing Adjustment Rule", adjustment_rule, "frequency"
    )


def preview_schedule(options: ScheduleOptions, lines: list[ScheduleLine]) -> list[dict]:
    """Return the schedule rows that would be created, grouped per line.

    Args:
        options: Shared schedule options.
        lines: Item and customer combinations to schedule.

    Returns:
        One dictionary per line holding the item, customer and the generated
        rate periods.
    """
    schedule = []

    for line in lines:
        periods = build_schedule(options.to_request(line))
        schedule.append(
            {
                "item_code": line.item_code,
                "customer": line.customer,
                "base_rate": flt(line.base_rate),
                "periods": [
                    {
                        "valid_from": period.valid_from,
                        "valid_upto": period.valid_upto,
                        "rate": period.rate,
                        "increment_count": period.increment_count,
                    }
                    for period in periods
                ],
            }
        )

    return schedule


def create_item_prices(options: ScheduleOptions, lines: list[ScheduleLine]) -> dict:
    """Create the Item Price records of a schedule.

    Periods that already have an overlapping Item Price for the same item,
    price list and customer are skipped, which makes the operation idempotent.

    Args:
        options: Shared schedule options.
        lines: Item and customer combinations to schedule.

    Returns:
        Counts of created and skipped rows, plus the names that were created.
    """
    created = []
    skipped = 0

    for line in lines:
        periods = build_schedule(options.to_request(line))
        for period in periods:
            if has_overlapping_price(options, line, period):
                skipped += 1
                continue

            created.append(insert_item_price(options, line, period))

    return {"created": created, "created_count": len(created), "skipped": skipped}


def has_overlapping_price(
    options: ScheduleOptions, line: ScheduleLine, period: RatePeriod
) -> bool:
    """Return whether an Item Price already covers ``period``.

    Args:
        options: Shared schedule options.
        line: Item and customer combination being scheduled.
        period: Generated period to check.

    Returns:
        ``True`` when an existing Item Price overlaps the period.
    """
    item_price = frappe.qb.DocType("Item Price")

    query = (
        frappe.qb.from_(item_price)
        .select(item_price.name)
        .where(item_price.item_code == line.item_code)
        .where(item_price.price_list == options.price_list)
        .where(item_price.uom == options.uom)
        .where((item_price.valid_from.isnull()) | (item_price.valid_from <= period.valid_upto))
        .where((item_price.valid_upto.isnull()) | (item_price.valid_upto >= period.valid_from))
    )

    if line.customer:
        query = query.where(item_price.customer == line.customer)
    else:
        query = query.where(item_price.customer.isnull())

    return bool(query.limit(1).run())


def insert_item_price(
    options: ScheduleOptions, line: ScheduleLine, period: RatePeriod
) -> str:
    """Insert a single Item Price record and return its name.

    These are ordinary Item Price records: the property is expressed by the
    item itself (each property owns a service item named after it), so no extra
    tagging is needed.

    Args:
        options: Shared schedule options.
        line: Item and customer combination being scheduled.
        period: Generated period to persist.

    Returns:
        Name of the created Item Price record.
    """
    doc = frappe.get_doc(
        {
            "doctype": "Item Price",
            "item_code": line.item_code,
            "price_list": options.price_list,
            "uom": options.uom,
            "customer": line.customer,
            "price_list_rate": flt(period.rate),
            "valid_from": period.valid_from,
            "valid_upto": period.valid_upto,
        }
    )
    doc.insert(ignore_permissions=True)

    return doc.name


def delete_existing_schedule(
    item_code: str, price_list: str, customer: str | None = None
) -> int:
    """Delete the Item Prices previously generated for an item.

    The scope is deliberately narrow - one item, one price list and one
    customer - which is exactly what a rent schedule creates. Prices belonging
    to any other item, price list or customer are never touched.

    Args:
        item_code: Item the schedule belongs to.
        price_list: Price list the schedule was created in.
        customer: Customer the schedule was scoped to, if any.

    Returns:
        Number of Item Price records deleted.
    """
    filters = {"item_code": item_code, "price_list": price_list}

    if customer:
        filters["customer"] = customer

    names = frappe.get_all("Item Price", filters=filters, pluck="name")
    for name in names:
        frappe.delete_doc("Item Price", name, ignore_permissions=True, force=True)

    return len(names)
