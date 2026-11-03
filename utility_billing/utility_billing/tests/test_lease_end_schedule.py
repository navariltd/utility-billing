"""Tests for the last billed day of a lease and the periods built up to it.

A request stores a lease of whole months by its anniversary (two months from
2025-10-01 end on 2025-12-01), so that end is the day after the last billed
day. No period may start on it. Periods are anchored on the lease start so a
start on the 31st does not drift to the 28th. Pure date maths: nothing is saved.
"""

from datetime import date
from math import ceil

from frappe.tests import UnitTestCase
from frappe.utils import add_days, add_months, getdate

from utility_billing.utility_billing.utils.item_price_schedule import (
	MONTHLY,
	QUARTERLY,
	YEARLY,
	IncrementRule,
	RateOverride,
	RatePeriod,
	ScheduleRequest,
	build_schedule,
	last_lease_day,
	months_per_period,
)
from utility_billing.utility_billing.utils.item_price_validation import build_manual_schedule

STARTS = (date(2025, 1, 1), date(2025, 1, 12), date(2025, 1, 15), date(2025, 1, 31))
LENGTHS = (1, 2, 9, 12)
FREQUENCIES = (MONTHLY, QUARTERLY, YEARLY)
MONTHLY_TEN_PERCENT = IncrementRule(interval_months=1, percentage=10)


def stored_end(start: date, months: int) -> date:
	"""The lease end validate_contract_dates stores for ``months`` from ``start``."""
	return getdate(add_months(start, months))


def schedule(start, end, frequency=MONTHLY, rule=None, base_rate=1000, **values):
	return build_schedule(
		ScheduleRequest(
			start_date=start,
			end_date=end,
			base_rate=base_rate,
			frequency=frequency,
			rule=rule or IncrementRule(),
			merge=False,
			**values,
		)
	)


class TestLastLeaseDay(UnitTestCase):
	"""Which stored lease ends are the day after the last billed day."""

	def test_an_anniversary_on_the_first_is_the_day_after_the_lease(self):
		self.assertEqual(last_lease_day(date(2025, 10, 1), date(2025, 12, 1)), date(2025, 11, 30))

	def test_an_anniversary_mid_month_is_the_day_after_the_lease(self):
		self.assertEqual(last_lease_day(date(2025, 1, 12), date(2026, 1, 12)), date(2026, 1, 11))

	def test_a_clamped_anniversary_of_the_31st_is_the_day_after_the_lease(self):
		self.assertEqual(last_lease_day(date(2025, 1, 31), date(2025, 2, 28)), date(2025, 2, 27))
		self.assertEqual(last_lease_day(date(2025, 1, 31), date(2025, 4, 30)), date(2025, 4, 29))

	def test_any_other_end_is_inclusive(self):
		self.assertEqual(last_lease_day(date(2025, 10, 1), date(2025, 11, 30)), date(2025, 11, 30))
		self.assertEqual(last_lease_day(date(2025, 4, 15), date(2027, 1, 1)), date(2027, 1, 1))

	def test_an_open_ended_lease_has_no_last_day(self):
		self.assertIsNone(last_lease_day(date(2025, 10, 1), None))

	def test_applying_it_twice_changes_nothing(self):
		for start in STARTS:
			for months in LENGTHS:
				last = last_lease_day(start, stored_end(start, months))
				with self.subTest(start=start, months=months):
					self.assertEqual(last_lease_day(start, last), last)


class TestPeriodsUpToTheLastDay(UnitTestCase):
	"""Every start, length and frequency stops on the last billed day."""

	def test_no_period_starts_on_the_stored_end(self):
		for start in STARTS:
			for months in LENGTHS:
				end = stored_end(start, months)
				for frequency in FREQUENCIES:
					step = months_per_period(frequency)
					periods = schedule(start, end, frequency)
					with self.subTest(start=start, months=months, frequency=frequency):
						self.assertEqual(len(periods), ceil(months / step))
						self.assertEqual(periods[-1].valid_upto, getdate(add_days(end, -1)))
						self.assertNotIn(end, [period.valid_from for period in periods])
						for index, period in enumerate(periods):
							self.assertEqual(period.valid_from, getdate(add_months(start, index * step)))
						for previous, current in zip(periods, periods[1:]):
							self.assertEqual(current.valid_from, getdate(add_days(previous.valid_upto, 1)))

	def test_increments_end_on_the_rate_owed_for_the_last_month(self):
		for start in STARTS:
			for months in LENGTHS:
				periods = schedule(start, stored_end(start, months), MONTHLY, MONTHLY_TEN_PERCENT)
				with self.subTest(start=start, months=months):
					self.assertAlmostEqual(periods[-1].rate, 1000 * (1 + 0.1 * (months - 1)))
					self.assertEqual(periods[-1].increment_count, months - 1)

	def test_a_start_on_the_31st_keeps_its_day(self):
		periods = schedule(date(2025, 1, 31), date(2025, 10, 31), MONTHLY, MONTHLY_TEN_PERCENT)

		self.assertEqual(len(periods), 9)
		self.assertEqual(periods[1].valid_from, date(2025, 2, 28))
		self.assertEqual(periods[1].valid_upto, date(2025, 3, 30))
		self.assertEqual(periods[2].valid_from, date(2025, 3, 31))
		self.assertEqual((periods[-1].valid_from, periods[-1].valid_upto), (date(2025, 9, 30), date(2025, 10, 30)))
		self.assertAlmostEqual(periods[1].rate, 1100)

	def test_the_reported_two_month_lease_has_two_periods(self):
		# USR 00016: 2025-10-01 for two months, stored as ending 2025-12-01.
		periods = schedule(
			date(2025, 10, 1),
			date(2025, 12, 1),
			MONTHLY,
			IncrementRule(interval_months=1, percentage=10),
			base_rate=20001,
		)

		self.assertEqual(
			[(period.valid_from, period.valid_upto, round(period.rate, 2)) for period in periods],
			[(date(2025, 10, 1), date(2025, 10, 31), 20001), (date(2025, 11, 1), date(2025, 11, 30), 22001.1)],
		)

	def test_an_inclusive_end_is_billed_up_to_and_including_it(self):
		periods = schedule(date(2025, 1, 1), date(2025, 11, 30))

		self.assertEqual(len(periods), 11)
		self.assertEqual(periods[-1].valid_upto, date(2025, 11, 30))

	def test_a_lease_ending_part_way_through_a_period_is_clipped(self):
		periods = schedule(date(2025, 1, 1), date(2025, 3, 1), QUARTERLY)

		self.assertEqual([(p.valid_from, p.valid_upto) for p in periods], [(date(2025, 1, 1), date(2025, 2, 28))])

	def test_an_open_ended_lease_still_stops_at_the_period_limit(self):
		periods = schedule(date(2025, 1, 31), None, MONTHLY, max_periods=14)

		self.assertEqual(len(periods), 14)
		self.assertEqual(periods[-1].valid_from, date(2026, 2, 28))

	def test_a_manual_rate_is_the_base_of_later_increments(self):
		periods = schedule(
			date(2025, 1, 1),
			date(2026, 1, 1),
			MONTHLY,
			MONTHLY_TEN_PERCENT,
			overrides=[RateOverride(from_date=date(2025, 4, 1), rate=5000)],
		)

		self.assertEqual([round(p.rate) for p in periods[:6]], [1000, 1100, 1200, 5000, 5500, 6000])
		self.assertEqual(periods[3].increment_count, 0)


class TestManualScheduleCoverage(UnitTestCase):
	"""A hand edited schedule has to reach the last billed day."""

	def periods(self, *ranges):
		return [RatePeriod(valid_from=a, valid_upto=b, rate=1000, increment_count=0) for a, b in ranges]

	def test_a_schedule_ending_the_day_before_the_stored_end_is_accepted(self):
		built = build_manual_schedule(
			self.periods((date(2025, 10, 1), date(2025, 10, 31)), (date(2025, 11, 1), date(2025, 11, 30))),
			date(2025, 10, 1),
			date(2025, 12, 1),
		)

		self.assertEqual(built[-1].valid_upto, date(2025, 11, 30))

	def test_a_schedule_running_on_to_the_stored_end_is_still_accepted(self):
		build_manual_schedule(
			self.periods((date(2025, 10, 1), date(2025, 11, 30)), (date(2025, 12, 1), date(2025, 12, 1))),
			date(2025, 10, 1),
			date(2025, 12, 1),
		)

	def test_a_schedule_stopping_earlier_is_refused(self):
		with self.assertRaises(ValueError):
			build_manual_schedule(
				self.periods((date(2025, 10, 1), date(2025, 11, 29))), date(2025, 10, 1), date(2025, 12, 1)
			)

	def test_an_inclusive_end_has_to_be_reached(self):
		with self.assertRaises(ValueError):
			build_manual_schedule(
				self.periods((date(2025, 10, 1), date(2025, 11, 29))), date(2025, 10, 1), date(2025, 11, 30)
			)
