"""Comparison tests: under Auto Repeat the Define preview and summary match develop.

Item Price schedules stop at the last billed day with periods anchored on the
start. Nothing can be created from the preview under Auto Repeat, so there it
keeps the schedule develop shows: up to and including the stored lease end,
each period starting the day after the previous one, and no list of priced
properties in the summary. The expected values below are develop's output.
"""

from datetime import date

import frappe
from frappe.tests import UnitTestCase
from frappe.tests.utils import FrappeTestCase

from utility_billing.utility_billing.tests import lease_fixtures as fx
from utility_billing.utility_billing.utils import item_price_actions
from utility_billing.utility_billing.utils.item_price_schedule import (
	MONTHLY,
	IncrementRule,
	RatePeriod,
	ScheduleRequest,
	build_schedule,
)
from utility_billing.utility_billing.utils.item_price_validation import build_manual_schedule

TEN_PERCENT = IncrementRule(interval_months=1, percentage=10)
A = "_Test Preview Compare A"
B = "_Test Preview Compare B"


def as_stored(start, end, base_rate=1000, rule=TEN_PERCENT):
	return build_schedule(
		ScheduleRequest(
			start_date=start,
			end_date=end,
			base_rate=base_rate,
			frequency=MONTHLY,
			rule=rule,
			merge=False,
			last_day_rules=False,
		)
	)


class TestScheduleAsOnDevelop(UnitTestCase):
	"""``last_day_rules`` off reproduces develop's schedules."""

	def test_the_period_on_the_stored_end_is_kept(self):
		periods = as_stored(date(2025, 10, 1), date(2025, 12, 1), base_rate=20001)

		self.assertEqual(
			[(p.valid_from, p.valid_upto, round(p.rate, 2)) for p in periods],
			[
				(date(2025, 10, 1), date(2025, 10, 31), 20001),
				(date(2025, 11, 1), date(2025, 11, 30), 22001.1),
				(date(2025, 12, 1), date(2025, 12, 1), 24001.2),
			],
		)

	def test_a_start_on_the_31st_drifts_as_before(self):
		periods = as_stored(date(2025, 1, 31), date(2025, 10, 31))

		self.assertEqual(len(periods), 10)
		self.assertEqual((periods[-1].valid_from, periods[-1].valid_upto), (date(2025, 10, 28), date(2025, 10, 31)))
		self.assertEqual(round(periods[-1].rate), 1800)

	def test_a_twelve_month_lease_mid_month_has_thirteen_periods(self):
		periods = as_stored(date(2025, 1, 15), date(2026, 1, 15))

		self.assertEqual(len(periods), 13)
		self.assertEqual((periods[-1].valid_from, round(periods[-1].rate)), (date(2026, 1, 15), 2200))

	def test_a_manual_schedule_has_to_reach_the_stored_end(self):
		periods = [RatePeriod(date(2025, 10, 1), date(2025, 11, 30), 1000, 0)]

		with self.assertRaises(ValueError):
			build_manual_schedule(periods, date(2025, 10, 1), date(2025, 12, 1), last_day_rules=False)
		build_manual_schedule(periods, date(2025, 10, 1), date(2025, 12, 1))


class TestPreviewByApproach(fx.SavepointMixin, FrappeTestCase):
	"""The Define preview and summary under each approach."""

	def setUp(self):
		super().setUp()
		for name in (A, B):
			fx.lease_property(name)

	def preview(self, request, properties, start):
		return item_price_actions.preview_item_price_schedule(
			request.name,
			frappe.as_json(properties),
			frappe.as_json({name: 1000 for name in properties}),
			start,
			None,
			fx.PRICE_LIST,
			fx.CUSTOMER,
			None,
			"[]",
			"Monthly",
			frappe.as_json({"interval_months": 1, "percentage": 10}),
		)

	def periods(self, preview):
		return [(p["valid_from"], p["valid_upto"], round(p["rate"])) for p in preview[0]["periods"]]

	def test_auto_repeat_preview_matches_develop(self):
		fx.use_approach("Auto Repeat")
		request = fx.make_request([(A, "2026-01-01", "2027-01-01")], "2026-01-01", "2027-01-01")

		periods = self.periods(self.preview(request, [A], "2026-01-01"))

		self.assertEqual(len(periods), 13)
		self.assertEqual(periods[-1], ("2027-01-01", "2027-01-01", 2200))

	def test_item_price_preview_stops_at_the_last_billed_day(self):
		fx.use_approach("Item Price")
		request = fx.make_request([(A, "2026-01-01", "2027-01-01")], "2026-01-01", "2027-01-01")

		periods = self.periods(self.preview(request, [A], "2026-01-01"))

		self.assertEqual(len(periods), 12)
		self.assertEqual(periods[-1], ("2026-12-01", "2026-12-31", 2100))

	def test_auto_repeat_preview_of_several_starts_is_not_refused(self):
		fx.use_approach("Auto Repeat")
		request = fx.make_request(
			[(A, "2026-01-01", "2027-01-01"), (B, "2026-04-15", "2027-01-01")], "2026-01-01", "2027-01-01"
		)

		self.assertEqual(len(self.preview(request, [A, B], "2026-04-15")), 2)

		fx.use_approach("Item Price")
		with self.assertRaisesRegex(frappe.ValidationError, "start on different dates"):
			self.preview(request, [A, B], "2026-04-15")

	def test_auto_repeat_summary_matches_develop(self):
		fx.use_approach("Auto Repeat")
		request = fx.make_request([(A, "2026-01-01", "2027-01-01")], "2026-01-01", "2027-01-01")

		self.assertEqual(sorted(item_price_actions.get_item_price_summary(request.name)), ["has_prices", "html"])

		fx.use_approach("Item Price")
		self.assertEqual(
			sorted(item_price_actions.get_item_price_summary(request.name)),
			["has_prices", "html", "priced_properties"],
		)
