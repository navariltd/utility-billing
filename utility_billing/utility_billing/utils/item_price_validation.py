"""Validation of manually defined Item Price schedules.

The ``Define Item Prices`` modal and the Item Price Summary both let a user
edit the generated schedule by hand. A hand edited schedule is only usable when
it still describes the whole contract period of its property, so it has to start
with the contract, run without gaps or overlaps and reach the contract end.

Generated schedules are produced by
``utility_billing.utility_billing.utils.item_price_schedule`` and never need
these checks. This module is free of database access so the rules can be unit
tested.
"""

from datetime import date

from frappe import _
from frappe.utils import add_days, cint, flt, formatdate, getdate

from utility_billing.utility_billing.utils.item_price_schedule import RatePeriod


def build_manual_schedule(
    periods: list[RatePeriod], start_date, end_date
) -> list[RatePeriod]:
    """Return the validated, ordered periods of a manual schedule.

    Args:
        periods: Manually defined ``RatePeriod`` rows, in any order.
        start_date: First date the schedule must cover.
        end_date: Last date the schedule must cover, or ``None`` when the
            contract is open ended.

    Returns:
        The periods ordered by ``valid_from``, normalised to dates and floats.

    Raises:
        ValueError: If a period is incomplete or the schedule does not form a
            gapless run covering the whole contract period.
    """
    ordered = _sort_by_start(periods)
    if not ordered:
        raise ValueError(_("Define at least one rent period."))

    normalized = [_normalize(period) for period in ordered]
    _validate_coverage(
        normalized,
        getdate(start_date),
        getdate(end_date) if end_date else None,
    )

    return normalized


def _sort_by_start(periods: list[RatePeriod]) -> list[RatePeriod]:
    """Return the periods ordered by their start date, tolerating blanks."""

    def start_of(period):
        value = getattr(period, "valid_from", None)
        return getdate(value) if value else date.min

    return sorted(periods or [], key=start_of)


def _normalize(period: RatePeriod) -> RatePeriod:
    """Return a period with clean dates and a non-negative rate."""
    valid_from = _require_date(getattr(period, "valid_from", None), _("From"))
    valid_upto = _require_date(getattr(period, "valid_upto", None), _("To"))

    if valid_upto < valid_from:
        raise ValueError(_("A rent period cannot end before it starts."))

    rate = flt(getattr(period, "rate", None))
    if rate < 0:
        raise ValueError(_("Rent amounts cannot be negative."))

    return RatePeriod(
        valid_from=valid_from,
        valid_upto=valid_upto,
        rate=rate,
        increment_count=cint(getattr(period, "increment_count", 0)),
    )


def _require_date(value, label: str) -> date:
    """Return ``value`` as a date, raising when it is missing."""
    if not value:
        raise ValueError(_("Every rent period needs a {0} date.").format(label))

    return getdate(value)


def _validate_coverage(
    periods: list[RatePeriod], start_date: date, end_date: date | None
) -> None:
    """Check that ``periods`` form a gapless run over the contract period.

    Args:
        periods: Ordered, normalised periods.
        start_date: First date the contract covers.
        end_date: Last date the contract covers, or ``None`` when open ended.

    Raises:
        ValueError: If the schedule starts after the contract, has a gap or an
            overlap, or stops before the contract end.
    """
    if periods[0].valid_from > start_date:
        raise ValueError(
            _("The schedule must start on or before {0}.").format(
                formatdate(start_date)
            )
        )

    for previous, current in zip(periods, periods[1:]):
        expected_start = add_days(previous.valid_upto, 1)
        if current.valid_from != expected_start:
            raise ValueError(
                _(
                    "Rent periods must run without gaps or overlaps: the period "
                    "after {0} has to start on {1}."
                ).format(formatdate(previous.valid_upto), formatdate(expected_start))
            )

    if end_date and periods[-1].valid_upto < end_date:
        raise ValueError(
            _("The schedule must cover the contract period up to {0}.").format(
                formatdate(end_date)
            )
        )
