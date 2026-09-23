"""Tests for the pure Item Price schedule maths.

These tests do not touch the database: only ``frappe.utils`` date helpers are
used, so the schedule can be verified in isolation.
"""

from datetime import date, timedelta

from frappe.tests import UnitTestCase

from utility_billing.utility_billing.utils.item_price_schedule import (
	LAST_ADJUSTED_AMOUNT,
	MONTHLY,
	ORIGINAL_AMOUNT,
	QUARTERLY,
	YEARLY,
	IncrementRule,
	RateOverride,
	RatePeriod,
	ScheduleRequest,
	apply_increment,
	build_schedule,
	increment_count,
	merge_by_rate,
	month_diff,
	months_per_period,
	period_end_date,
)


class TestScheduleMaths(UnitTestCase):
	"""Rate period generation over a lease period."""

	def test_months_per_period_defaults_to_monthly_for_unknown_frequency(self):
		self.assertEqual(months_per_period(MONTHLY), 1)
		self.assertEqual(months_per_period(QUARTERLY), 3)
		self.assertEqual(months_per_period(YEARLY), 12)
		self.assertEqual(months_per_period("Fortnightly"), 1)

	def test_period_end_date_is_day_before_next_period(self):
		self.assertEqual(period_end_date(date(2026, 1, 1), MONTHLY), date(2026, 1, 31))
		self.assertEqual(period_end_date(date(2026, 1, 1), QUARTERLY), date(2026, 3, 31))
		self.assertEqual(period_end_date(date(2026, 1, 1), YEARLY), date(2026, 12, 31))

	def test_month_diff_ignores_partial_months(self):
		self.assertEqual(month_diff(date(2026, 1, 1), date(2026, 3, 1)), 2)
		self.assertEqual(month_diff(date(2026, 1, 15), date(2026, 3, 14)), 1)
		self.assertEqual(month_diff(date(2026, 3, 1), date(2026, 1, 1)), 0)


class TestIncrementRule(UnitTestCase):
	"""Increment application to a base rate."""

	def test_disabled_rule_never_increments(self):
		rule = IncrementRule(interval_months=0, percentage=5)
		self.assertFalse(rule.enabled)
		self.assertEqual(apply_increment(1000, rule, 120), 1000)

	def test_first_increment_applies_after_interval(self):
		rule = IncrementRule(interval_months=12, percentage=5)
		self.assertEqual(apply_increment(1000, rule, 11), 1000)
		self.assertEqual(apply_increment(1000, rule, 12), 1050)

	def test_effective_after_months_delays_first_increment(self):
		rule = IncrementRule(interval_months=12, percentage=5, effective_after_months=12)
		self.assertEqual(apply_increment(1000, rule, 23), 1000)
		self.assertEqual(apply_increment(1000, rule, 24), 1050)

	def test_increment_count_is_zero_before_first_increment(self):
		rule = IncrementRule(interval_months=12, percentage=5)
		self.assertEqual(increment_count(rule, 6), 0)
		self.assertEqual(increment_count(rule, 12), 1)
		self.assertEqual(increment_count(rule, 36), 3)


class TestAdjustmentBasis(UnitTestCase):
	"""Original amount grows linearly, last adjusted amount compounds."""

	def test_default_basis_is_original_amount(self):
		rule = IncrementRule(interval_months=12, percentage=5)
		self.assertEqual(rule.basis, ORIGINAL_AMOUNT)
		self.assertFalse(rule.compounds)

	def test_original_amount_basis_adds_percentage_of_the_base_rate(self):
		rule = IncrementRule(interval_months=12, percentage=5, basis=ORIGINAL_AMOUNT)

		self.assertEqual(apply_increment(1000, rule, 12), 1050)
		self.assertEqual(apply_increment(1000, rule, 24), 1100)
		self.assertEqual(apply_increment(1000, rule, 36), 1150)

	def test_last_adjusted_amount_basis_compounds(self):
		rule = IncrementRule(
			interval_months=12, percentage=5, basis=LAST_ADJUSTED_AMOUNT
		)
		self.assertTrue(rule.compounds)

		self.assertEqual(apply_increment(1000, rule, 12), 1050)
		self.assertAlmostEqual(apply_increment(1000, rule, 24), 1102.5, places=4)
		self.assertAlmostEqual(apply_increment(1000, rule, 36), 1157.625, places=4)

	def test_compounding_has_no_upper_limit(self):
		rule = IncrementRule(interval_months=12, percentage=10, basis=LAST_ADJUSTED_AMOUNT)

		self.assertEqual(apply_increment(1000, rule, 12), 1100)
		self.assertAlmostEqual(apply_increment(1000, rule, 24), 1210, places=4)
		self.assertAlmostEqual(apply_increment(1000, rule, 36), 1331, places=4)


class TestBuildSchedule(UnitTestCase):
	"""Rate period generation for a lease."""

	def test_schedule_covers_full_lease_without_gaps(self):
		request = ScheduleRequest(
			start_date=date(2026, 1, 1),
			end_date=date(2026, 3, 31),
			base_rate=1000,
			merge=False,
		)

		periods = build_schedule(request)

		self.assertEqual(len(periods), 3)
		self.assertEqual(periods[0].valid_from, date(2026, 1, 1))
		self.assertEqual(periods[0].valid_upto, date(2026, 1, 31))
		self.assertEqual(periods[-1].valid_upto, date(2026, 3, 31))

	def test_schedule_applies_yearly_increment_and_caps_at_lease_end(self):
		request = ScheduleRequest(
			start_date=date(2026, 1, 1),
			end_date=date(2027, 12, 31),
			base_rate=100000,
			rule=IncrementRule(interval_months=12, percentage=5),
			merge=False,
		)

		periods = build_schedule(request)

		self.assertEqual(len(periods), 24)
		self.assertEqual(periods[0].rate, 100000)
		self.assertEqual(periods[11].rate, 100000)
		self.assertEqual(periods[12].rate, 105000)
		self.assertEqual(periods[23].rate, 105000)
		self.assertEqual(periods[-1].valid_upto, date(2027, 12, 31))

	def test_manual_override_replaces_generated_rate(self):
		request = ScheduleRequest(
			start_date=date(2026, 1, 1),
			end_date=date(2026, 3, 31),
			base_rate=1000,
			overrides=[RateOverride(from_date=date(2026, 2, 1), rate=2000)],
			merge=False,
		)

		periods = build_schedule(request)

		self.assertEqual(periods[0].rate, 1000)
		self.assertEqual(periods[1].rate, 2000)
		self.assertEqual(periods[2].rate, 2000)

	def test_override_becomes_base_for_further_increments(self):
		request = ScheduleRequest(
			start_date=date(2026, 1, 1),
			end_date=date(2026, 12, 31),
			base_rate=1000,
			rule=IncrementRule(interval_months=6, percentage=10),
			overrides=[RateOverride(from_date=date(2026, 3, 1), rate=2000)],
			merge=False,
		)

		periods = build_schedule(request)

		self.assertEqual(periods[0].rate, 1000)
		self.assertEqual(periods[1].rate, 1000)
		self.assertEqual(periods[2].rate, 2000)
		self.assertEqual(periods[5].rate, 2000)
		# The override starts in March, so its first increment lands in September.
		self.assertEqual(periods[8].rate, 2200)
		self.assertEqual(periods[8].increment_count, 1)

	def test_open_ended_schedule_stops_at_max_periods(self):
		request = ScheduleRequest(
			start_date=date(2026, 1, 1),
			end_date=None,
			base_rate=1000,
			max_periods=5,
			merge=False,
		)

		periods = build_schedule(request)

		self.assertEqual(len(periods), 5)
		self.assertEqual(periods[-1].valid_upto, date(2026, 5, 31))

	def test_zero_base_rate_produces_zero_rates(self):
		request = ScheduleRequest(
			start_date=date(2026, 1, 1),
			end_date=date(2026, 2, 28),
			base_rate=0,
			rule=IncrementRule(interval_months=1, percentage=5),
			merge=False,
		)

		periods = build_schedule(request)

		self.assertEqual([period.rate for period in periods], [0, 0])

	def test_end_date_before_start_date_is_rejected(self):
		request = ScheduleRequest(
			start_date=date(2026, 3, 1), end_date=date(2026, 1, 1), base_rate=1000,
			merge=False,
		)

		with self.assertRaises(ValueError):
			build_schedule(request)

	def test_increment_switches_exactly_on_the_boundary_period(self):
		request = ScheduleRequest(
			start_date=date(2026, 1, 1),
			end_date=date(2027, 12, 31),
			base_rate=1000,
			rule=IncrementRule(interval_months=12, percentage=5),
			merge=False,
		)

		periods = build_schedule(request)

		# Every period up to month 11 keeps the base rate; month 12 onwards
		# carries the increment, and no period is missed or duplicated.
		self.assertTrue(all(period.rate == 1000 for period in periods[:12]))
		self.assertTrue(all(period.rate == 1050 for period in periods[12:]))

	def test_periods_are_contiguous_with_no_gaps_or_overlaps(self):
		request = ScheduleRequest(
			start_date=date(2026, 1, 1),
			end_date=date(2027, 6, 30),
			base_rate=1000,
			rule=IncrementRule(interval_months=6, percentage=5),
			merge=False,
		)

		periods = build_schedule(request)

		self.assertEqual(periods[0].valid_from, date(2026, 1, 1))
		self.assertEqual(periods[-1].valid_upto, date(2027, 6, 30))

		for previous, current in zip(periods, periods[1:]):
			self.assertEqual(
				current.valid_from,
				previous.valid_upto + timedelta(days=1),
				"periods must run back to back",
			)

	def test_quarterly_periods_increment_every_two_periods_at_6_months(self):
		request = ScheduleRequest(
			start_date=date(2026, 1, 1),
			end_date=date(2026, 12, 31),
			base_rate=1000,
			frequency=QUARTERLY,
			rule=IncrementRule(interval_months=6, percentage=10, basis=ORIGINAL_AMOUNT),
			merge=False,
		)

		periods = build_schedule(request)

		self.assertEqual(len(periods), 4)
		self.assertEqual([period.rate for period in periods], [1000, 1000, 1100, 1100])

	def test_long_constant_rate_lease_reaches_the_end_date(self):
		# A monthly lease longer than the default safety limit must still cover
		# the whole contract before periods are merged into one.
		request = ScheduleRequest(
			start_date=date(2026, 9, 1),
			end_date=date(2038, 11, 1),
			base_rate=9000,
			frequency=MONTHLY,
		)

		periods = build_schedule(request)

		self.assertEqual(len(periods), 1)
		self.assertEqual(periods[0].valid_from, date(2026, 9, 1))
		self.assertEqual(periods[0].valid_upto, date(2038, 11, 1))

	def test_long_lease_with_increments_reaches_the_end_date(self):
		request = ScheduleRequest(
			start_date=date(2026, 9, 1),
			end_date=date(2038, 11, 1),
			base_rate=9000,
			frequency=MONTHLY,
			rule=IncrementRule(interval_months=12, percentage=5, basis=ORIGINAL_AMOUNT),
		)

		periods = build_schedule(request)

		self.assertEqual(periods[0].valid_from, date(2026, 9, 1))
		self.assertEqual(periods[-1].valid_upto, date(2038, 11, 1))


class TestMergeByRate(UnitTestCase):
	"""Consecutive periods sharing a rate become one Item Price period."""

	def _period(self, start, end, rate):
		return RatePeriod(
			valid_from=date.fromisoformat(start),
			valid_upto=date.fromisoformat(end),
			rate=rate,
			increment_count=0,
		)

	def test_unchanged_rates_collapse_into_a_single_period(self):
		periods = [
			self._period("2026-01-01", "2026-01-31", 1000),
			self._period("2026-02-01", "2026-02-28", 1000),
			self._period("2026-03-01", "2026-03-31", 1000),
		]

		merged = merge_by_rate(periods)

		self.assertEqual(len(merged), 1)
		self.assertEqual(merged[0].valid_from, date(2026, 1, 1))
		self.assertEqual(merged[0].valid_upto, date(2026, 3, 31))
		self.assertEqual(merged[0].rate, 1000)

	def test_periods_split_wherever_the_rate_changes(self):
		periods = [
			self._period("2026-01-01", "2026-01-31", 1000),
			self._period("2026-02-01", "2026-02-28", 1000),
			self._period("2026-03-01", "2026-03-31", 1100),
			self._period("2026-04-01", "2026-04-30", 1100),
			self._period("2026-05-01", "2026-05-31", 1200),
		]

		merged = merge_by_rate(periods)

		self.assertEqual(len(merged), 3)
		self.assertEqual(
			[(p.valid_from, p.valid_upto, p.rate) for p in merged],
			[
				(date(2026, 1, 1), date(2026, 2, 28), 1000),
				(date(2026, 3, 1), date(2026, 4, 30), 1100),
				(date(2026, 5, 1), date(2026, 5, 31), 1200),
			],
		)

	def test_rates_differing_by_a_cent_are_not_merged(self):
		periods = [
			self._period("2026-01-01", "2026-01-31", 1000.00),
			self._period("2026-02-01", "2026-02-28", 1000.01),
		]

		self.assertEqual(len(merge_by_rate(periods)), 2)

	def test_float_noise_does_not_prevent_merging(self):
		periods = [
			self._period("2026-01-01", "2026-01-31", 1000),
			self._period("2026-02-01", "2026-02-28", 1000.000000001),
		]

		self.assertEqual(len(merge_by_rate(periods)), 1)

	def test_single_period_is_returned_unchanged(self):
		periods = [self._period("2026-01-01", "2026-01-31", 1000)]

		self.assertEqual(merge_by_rate(periods), periods)

	def test_empty_schedule_returns_empty(self):
		self.assertEqual(merge_by_rate([]), [])

	def test_unordered_periods_are_rejected(self):
		periods = [
			self._period("2026-02-01", "2026-02-28", 1000),
			self._period("2026-01-01", "2026-01-31", 1000),
		]

		with self.assertRaises(ValueError):
			merge_by_rate(periods)

	def test_build_schedule_merges_by_default(self):
		request = ScheduleRequest(
			start_date=date(2026, 1, 1), end_date=date(2026, 12, 31), base_rate=1000
		)

		periods = build_schedule(request)

		self.assertEqual(len(periods), 1)
		self.assertEqual(periods[0].valid_from, date(2026, 1, 1))
		self.assertEqual(periods[0].valid_upto, date(2026, 12, 31))

	def test_build_schedule_can_return_unmerged_periods(self):
		request = ScheduleRequest(
			start_date=date(2026, 1, 1),
			end_date=date(2026, 12, 31),
			base_rate=1000,
			merge=False,
		)

		self.assertEqual(len(build_schedule(request)), 12)
