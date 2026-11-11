"""Item Price schedule generation for recurring rental billing.

This module turns a lease period plus an increment rule into a list of dated
rate periods. The output is used to create ``Item Price`` records instead of
relying on ``Auto Repeat`` documents when the configured billing approach is
``Item Price``.

The module is intentionally free of database access so that the schedule maths
can be unit tested. Database work lives in
``utility_billing.utility_billing.utils.item_prices``.
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Iterable

from frappe.utils import add_days, add_months, get_last_day, getdate

# Frequency values used by ``Billing Adjustment Rule.frequency``.
DAILY = "Daily"
WEEKLY = "Weekly"
MONTHLY = "Monthly"
QUARTERLY = "Quarterly"
HALF_YEARLY = "Half-yearly"
YEARLY = "Yearly"

# Number of months covered by one billing period of each frequency.
MONTHS_PER_PERIOD = {
    MONTHLY: 1,
    QUARTERLY: 3,
    HALF_YEARLY: 6,
    YEARLY: 12,
}

# Fallback when a frequency is not covered by ``MONTHS_PER_PERIOD``.
DEFAULT_MONTHS_PER_PERIOD = 1

# How each increment is calculated, mirroring
# ``Billing Adjustment Rule.adjustment_basis``.
ORIGINAL_AMOUNT = "Original Amount"
LAST_ADJUSTED_AMOUNT = "Last Adjusted Amount"

DEFAULT_ADJUSTMENT_BASIS = ORIGINAL_AMOUNT


@dataclass
class RatePeriod:
    """A single rate row of a generated Item Price schedule.

    Attributes:
        valid_from: First day the rate applies.
        valid_upto: Last day the rate applies, inclusive.
        rate: Rate for the period.
        increment_count: Number of increments already applied to ``rate``.
    """

    valid_from: date
    valid_upto: date
    rate: float
    increment_count: int


@dataclass
class RateOverride:
    """A manually entered rate period that replaces generated periods.

    Attributes:
        from_date: First day the manual rate applies.
        rate: Manually defined rate.
    """

    from_date: date
    rate: float


@dataclass
class IncrementRule:
    """Increment behaviour applied while generating the schedule.

    Attributes:
        interval_months: Months between two increments. ``0`` disables them.
        percentage: Percentage added at every increment.
        effective_after_months: Grace period before the first increment.
        basis: Whether each increment is calculated on the original rate
            (``ORIGINAL_AMOUNT``) or on the last adjusted rate
            (``LAST_ADJUSTED_AMOUNT``).
    """

    interval_months: float = 0
    percentage: float = 0
    effective_after_months: float = 0
    basis: str = DEFAULT_ADJUSTMENT_BASIS

    @property
    def enabled(self) -> bool:
        """Whether the rule actually increments anything."""
        return self.interval_months > 0 and self.percentage > 0

    @property
    def compounds(self) -> bool:
        """Whether increments are calculated on the last adjusted rate."""
        return self.basis == LAST_ADJUSTED_AMOUNT


@dataclass
class ScheduleRequest:
    """Input required to build a rate schedule.

    Attributes:
        start_date: Lease start date, first day of the first period.
        end_date: Lease end date, inclusive. ``None`` means open ended, in
            which case periods are generated until ``max_periods`` is reached.
        base_rate: Rate of the first period.
        frequency: Billing frequency, see ``MONTHS_PER_PERIOD``.
        rule: Increment rule applied to the schedule.
        max_periods: Safety limit when ``end_date`` is not provided.
        overrides: Manually entered rates, ordered by ``from_date``.
        merge: Whether consecutive periods with the same rate are collapsed
            into a single period. Enabled by default so one ``Item Price``
            covers each stretch where the rate does not change.
        manual_periods: Fully hand edited periods. When supplied they replace
            generation entirely and are validated against the contract period.
        last_day_rules: Whether the schedule stops at the lease's last billed
            day with periods anchored on the start (see ``build_schedule``).
            Off only for the read only preview under Auto Repeat, which keeps
            the schedule it always showed there.
    """

    start_date: date
    end_date: date | None
    base_rate: float
    frequency: str = MONTHLY
    rule: IncrementRule = field(default_factory=IncrementRule)
    max_periods: int = 120
    overrides: list[RateOverride] = field(default_factory=list)
    merge: bool = True
    manual_periods: list[RatePeriod] | None = None
    last_day_rules: bool = True


def months_per_period(frequency: str) -> int:
    """Return how many months a billing period of ``frequency`` covers.

    Args:
        frequency: Value of ``Billing Adjustment Rule.frequency``.

    Returns:
        Number of months covered by one period. Unknown frequencies fall back
        to a single month so that a schedule is always produced.
    """
    return MONTHS_PER_PERIOD.get(frequency, DEFAULT_MONTHS_PER_PERIOD)


def period_end_date(start: date, frequency: str) -> date:
    """Return the inclusive end date of the period starting on ``start``.

    Args:
        start: First day of the period.
        frequency: Billing frequency.

    Returns:
        Last day of the period, one day before the next period starts.
    """
    return add_days(add_months(start, months_per_period(frequency)), -1)


def last_lease_day(start_date: date, end_date: date | None) -> date | None:
    """Return the last day a lease is billed for.

    A request records a lease of whole months by its anniversary: two months
    from 2025-10-01 end on 2025-12-01 (see ``validate_contract_dates``). That
    day starts the next month, so the day before is the last one billed. Any
    other end date is inclusive as entered.

    A start late in the month is clamped by ``add_months`` (one month from
    2025-01-31 ends on 2025-02-28), so the next anniversary is checked too.

    Args:
        start_date: First day of the lease.
        end_date: Lease end as stored, or ``None`` when open ended.

    Returns:
        The last billed day, or ``end_date`` itself when it is not an
        anniversary of ``start_date``.
    """
    if not end_date:
        return end_date

    start_date, end_date = getdate(start_date), getdate(end_date)
    if end_date <= start_date:
        return end_date

    months = month_diff(start_date, end_date)
    anniversaries = (getdate(add_months(start_date, months)), getdate(add_months(start_date, months + 1)))
    if end_date in anniversaries:
        return getdate(add_days(end_date, -1))

    return end_date


def ends_whole_months(start_date: date, end_date: date | None) -> bool:
    """Return whether a lease starting on the 1st ends on the last day of a month.

    Such an end is inclusive: 2030-01-01 to 2030-02-28 is two whole months.
    ``last_lease_day`` already returns it unchanged, since the last day of a
    month is never an anniversary of a 1st.
    """
    if not (start_date and end_date):
        return False

    start_date, end_date = getdate(start_date), getdate(end_date)
    return start_date.day == 1 and start_date <= end_date == getdate(get_last_day(end_date))


def whole_lease_months(start_date: date, end_date: date) -> int:
    """Return the months of a lease, counting an inclusive month end as a whole month.

    2030-01-01 to 2030-02-28 and the anniversary form 2030-01-01 to
    2030-03-01 are both two months. Any other pair is ``month_diff``.
    """
    start_date, end_date = getdate(start_date), getdate(end_date)
    if ends_whole_months(start_date, end_date):
        end_date = getdate(add_days(end_date, 1))

    return month_diff(start_date, end_date)

def increment_count(rule: IncrementRule, months_elapsed: int) -> int:
    """Return how many increments have been applied after ``months_elapsed``.

    The first increment applies once ``effective_after_months`` plus one
    ``interval_months`` has elapsed, and then repeats every
    ``interval_months``.

    Args:
        rule: Increment rule to evaluate.
        months_elapsed: Whole months elapsed since the first rate started.

    Returns:
        Number of increments applied, ``0`` when the rule is disabled or the
        first increment has not been reached yet.
    """
    if not rule.enabled:
        return 0

    months = months_elapsed - float(rule.effective_after_months)
    if months < float(rule.interval_months):
        return 0

    return int(months // float(rule.interval_months))


def apply_increment(base_rate: float, rule: IncrementRule, months_elapsed: int) -> float:
    """Return the rate after ``months_elapsed`` months of a lease.

    The basis controls how each increment is applied:

    - ``ORIGINAL_AMOUNT``: every increment adds ``percentage`` of ``base_rate``,
      so the rate grows linearly.
    - ``LAST_ADJUSTED_AMOUNT``: every increment adds ``percentage`` of the
      previous period's rate, so the rate compounds.

    Args:
        base_rate: Rate of the first period.
        rule: Increment rule to apply.
        months_elapsed: Whole months elapsed since the base rate started.

    Returns:
        Rate for the period.
    """
    count = increment_count(rule, months_elapsed)
    if not count:
        return base_rate

    share = float(rule.percentage) / 100.0
    if rule.compounds:
        return base_rate * ((1 + share) ** count)

    return base_rate * (1 + (share * count))


def build_schedule(request: ScheduleRequest) -> list[RatePeriod]:
    """Build the dated rate periods covering a lease.

    Periods run from ``request.start_date`` until the last billed day of the
    lease (see ``last_lease_day``): a lease end falling whole months after the
    start is the day after the lease, so no period starts on it. Every period
    is anchored on the start, so a lease starting on the 31st keeps its day
    instead of drifting to the 28th after February, and increments are counted
    in periods for the same reason. A manual override starting on the first
    day of a period replaces the generated rate from that period onwards and
    becomes the base for subsequent increments. When
    ``request.manual_periods`` is set the periods are used as-is after being
    validated against the contract period.

    Args:
        request: Schedule definition.

    Returns:
        Ordered list of ``RatePeriod`` rows covering the lease.

    Raises:
        ValueError: If the end date is before the start date, or a manual
            schedule does not cover the contract period.
    """
    start_date = getdate(request.start_date)
    end_date = getdate(request.end_date) if request.end_date else None

    if end_date and end_date < start_date:
        raise ValueError("Schedule end date cannot be before the start date.")

    if request.manual_periods is not None:
        from utility_billing.utility_billing.utils.item_price_validation import (
            build_manual_schedule,
        )

        return build_manual_schedule(
            request.manual_periods, start_date, end_date, last_day_rules=request.last_day_rules
        )

    if not request.last_day_rules:
        periods = _periods_to_stored_end(request, start_date, end_date)
        return merge_by_rate(periods) if request.merge else periods

    end_date = last_lease_day(start_date, end_date)
    overrides = _index_overrides(request.overrides)
    base_rate = float(request.base_rate or 0)
    step = months_per_period(request.frequency)

    periods: list[RatePeriod] = []
    current_start = start_date
    applied_override = None
    # Index of the period the current rate is anchored on: the first one, or
    # the period a manual override starts on.
    anchor_index = 0
    limit = _period_limit(request, start_date, end_date)

    while len(periods) < limit:
        override = overrides.pop(current_start, None)
        if override is not None:
            applied_override = override
            anchor_index = len(periods)

        anchor_rate = float(applied_override.rate) if applied_override is not None else base_rate

        months_elapsed = (len(periods) - anchor_index) * step
        rate = apply_increment(anchor_rate, request.rule, months_elapsed)

        current_end = getdate(add_days(add_months(start_date, (len(periods) + 1) * step), -1))
        if end_date and current_end > end_date:
            current_end = end_date

        periods.append(
            RatePeriod(
                valid_from=current_start,
                valid_upto=current_end,
                rate=rate,
                increment_count=increment_count(request.rule, months_elapsed),
            )
        )

        if end_date and current_end >= end_date:
            break

        current_start = getdate(add_months(start_date, len(periods) * step))

    return merge_by_rate(periods) if request.merge else periods


def _periods_to_stored_end(
    request: ScheduleRequest, start_date: date, end_date: date | None
) -> list[RatePeriod]:
    """Return the periods up to and including the stored lease end.

    Each period starts the day after the previous one ends, and increments
    count calendar months. This is the schedule the Auto Repeat preview has
    always shown; Item Price schedules use ``build_schedule`` with
    ``last_day_rules`` on.
    """
    overrides = _index_overrides(request.overrides)
    base_rate = float(request.base_rate or 0)

    periods: list[RatePeriod] = []
    current_start = start_date
    applied_override = None
    limit = _period_limit(request, start_date, end_date)

    while len(periods) < limit:
        override = overrides.pop(current_start, None)
        if override is not None:
            applied_override = override

        if applied_override is not None:
            anchor_date = getdate(applied_override.from_date)
            anchor_rate = float(applied_override.rate)
        else:
            anchor_date = start_date
            anchor_rate = base_rate

        months_elapsed = month_diff(anchor_date, current_start)
        rate = apply_increment(anchor_rate, request.rule, months_elapsed)

        current_end = period_end_date(current_start, request.frequency)
        if end_date and current_end > end_date:
            current_end = end_date

        periods.append(
            RatePeriod(
                valid_from=current_start,
                valid_upto=current_end,
                rate=rate,
                increment_count=increment_count(request.rule, months_elapsed),
            )
        )

        if end_date and current_end >= end_date:
            break

        current_start = add_days(current_end, 1)

    return periods


def _period_limit(
    request: ScheduleRequest, start_date: date, end_date: date | None
) -> int:
    """Return how many periods may be generated before generation gives up.

    ``max_periods`` is only a safety net for open ended leases. When the lease
    end is known the limit is raised to the number of periods the span can hold,
    so a long lease is never truncated before its end date (and then merged).

    Args:
        request: Schedule definition.
        start_date: First day of the lease.
        end_date: Last day of the lease, or ``None`` when open ended.

    Returns:
        Maximum number of periods to generate.
    """
    if not end_date:
        return request.max_periods

    return max(request.max_periods, month_diff(start_date, end_date) + 2)


def merge_by_rate(periods: list[RatePeriod]) -> list[RatePeriod]:
    """Merge consecutive periods sharing a rate.

    Thin wrapper around ``item_price_periods.merge_by_rate`` so callers of this
    module do not need a second import. Imported lazily because
    ``item_price_periods`` reads ``RatePeriod`` from this module.

    Args:
        periods: Ordered periods to merge.

    Returns:
        Periods with consecutive equal rates collapsed into one.
    """
    from utility_billing.utility_billing.utils.item_price_periods import (
        merge_by_rate as _merge,
    )

    return _merge(periods)


def month_diff(start: date, end: date) -> int:
    """Return the number of whole months between two dates.

    Args:
        start: Earlier date.
        end: Later date.

    Returns:
        Whole months between the dates, never negative.
    """
    months = (end.year - start.year) * 12 + (end.month - start.month)
    if end.day < start.day:
        months -= 1

    return max(months, 0)


def _index_overrides(overrides: Iterable[RateOverride]) -> dict[date, RateOverride]:
    """Return manual overrides keyed by their ``from_date``."""
    return {getdate(override.from_date): override for override in overrides or []}
