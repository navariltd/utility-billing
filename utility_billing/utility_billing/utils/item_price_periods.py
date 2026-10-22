"""Collapsing generated rate periods into one period per rate.

Billing periods exist so a rate can change on a known date, but a single
``Item Price`` is enough to describe a stretch where the rate never changes.
This module turns the per-period output of
``utility_billing.utility_billing.utils.item_price_schedule`` into the minimal
set of periods needed, so a five year lease with a yearly increment produces
five ``Item Price`` records rather than sixty.
"""

from dataclasses import replace

from utility_billing.utility_billing.utils.item_price_schedule import RatePeriod

# Rates are compared to the cent, so floating point noise from applying
# percentages does not split a period unnecessarily.
RATE_PRECISION = 2


def merge_by_rate(periods: list[RatePeriod]) -> list[RatePeriod]:
    """Merge consecutive periods that share the same rate.

    Args:
        periods: Ordered periods, typically from ``build_schedule``.

    Returns:
        The periods with consecutive equal rates merged into one, keeping the
        first period's ``valid_from`` and the last period's ``valid_upto``.

    Raises:
        ValueError: If the periods are not in ascending date order.
    """
    if not periods:
        return []

    merged: list[RatePeriod] = []

    for period in periods:
        if merged and period.valid_from <= merged[-1].valid_from:
            raise ValueError("Periods must be ordered by start date to be merged.")

        if merged and same_rate(merged[-1].rate, period.rate):
            merged[-1] = replace(merged[-1], valid_upto=period.valid_upto)
            continue

        merged.append(period)

    return merged


def same_rate(first: float, second: float) -> bool:
    """Return whether two rates are equal once rounded to cents.

    Args:
        first: First rate.
        second: Second rate.

    Returns:
        ``True`` when both rates round to the same value at cents precision.
    """
    return round(float(first or 0), RATE_PRECISION) == round(
        float(second or 0), RATE_PRECISION
    )
