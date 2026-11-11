"""Tests for leases starting on the 1st that end on the last day of a month.

Such a lease counts whole months and its end is inclusive: 2030-01-01 to
2030-02-28 is two months. Ends are kept as typed: an end on the 1st, the
anniversary form every existing request uses, keeps working and gives the same
Item Prices, and an end inside a month is billed up to that day. Any other
start day keeps today's handling exactly.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from utility_billing.utility_billing.tests import lease_fixtures as fx
from utility_billing.utility_billing.tests.line_request_fixtures import P1, P2, make_request, setup_items
from utility_billing.utility_billing.utils import item_price_actions, request_prices
from utility_billing.utility_billing.utils.item_price_schedule import (
	IncrementRule,
	ScheduleRequest,
	build_schedule,
	last_lease_day,
)

# Start, end as typed, end as stored, Contract Length (Months), last billed day
CASES = [
	("2030-01-01", "2030-12-31", "2030-12-31", 12, "2030-12-31"),
	("2030-02-01", "2030-02-28", "2030-02-28", 1, "2030-02-28"),
	("2030-11-01", "2030-11-30", "2030-11-30", 1, "2030-11-30"),
	("2030-01-01", "2030-01-31", "2030-01-31", 1, "2030-01-31"),
	# An end inside a month is left as typed
	("2030-01-01", "2030-01-30", "2030-01-30", 0, "2030-01-30"),
	# The anniversary form of existing requests
	("2030-01-01", "2030-03-01", "2030-03-01", 2, "2030-02-28"),
	# Any other start day keeps today's dates and length
	("2030-01-15", "2030-02-14", "2030-02-14", 0, "2030-02-14"),
	("2030-01-15", "2030-02-15", "2030-02-15", 1, "2030-02-14"),
]

INCREMENT = {"interval_months": 1, "percentage": 10}


def request_dates(start, end, length=None):
	"""Return the end and length a request stores for the dates typed."""
	request = frappe.new_doc("Utility Service Request")
	request.update({"start_date": start, "end_date": end, "contract_length_months": length})
	request.validate_contract_dates()
	return str(request.end_date) if request.end_date else None, request.contract_length_months


class TestRequestDates(FrappeTestCase):
	def test_each_case_stores_its_end_and_length(self):
		for start, typed, stored, length, _last in CASES:
			with self.subTest(start=start, end=typed):
				self.assertEqual(request_dates(start, typed), (stored, length))

	def test_each_case_bills_up_to_its_last_day(self):
		for start, _typed, stored, _length, last in CASES:
			with self.subTest(start=start, end=stored):
				self.assertEqual(str(last_lease_day(frappe.utils.getdate(start), frappe.utils.getdate(stored))), last)

	def test_a_length_without_an_end_keeps_the_anniversary(self):
		# Only the form fills the month end; the API and the portal are unchanged
		self.assertEqual(request_dates("2030-01-01", None, 2), ("2030-03-01", 2))

	def test_a_part_month_length_is_refused_from_the_1st(self):
		with self.assertRaises(frappe.ValidationError):
			request_dates("2030-01-01", None, 1.5)

	def rows(self, start, end, row_start, row_end=None):
		request = frappe.new_doc("Utility Service Request")
		request.update({"start_date": start, "end_date": end})
		request.append("requested_properties", {"utility_property": P1, "start_date": row_start, "end_date": row_end})
		request.validate_contract_dates()
		request.validate_child_items()
		row = request.requested_properties[0]
		return str(row.end_date) if row.end_date else None, row.contract_length_months

	def test_a_row_from_the_1st_counts_whole_months(self):
		self.assertEqual(self.rows("2030-01-01", "2030-12-31", "2030-03-01", "2030-05-31"), ("2030-05-31", 3))
		self.assertEqual(self.rows("2030-01-01", "2030-12-31", "2030-03-01", "2030-05-20"), ("2030-05-20", 2))

	def test_a_row_from_the_28th_is_refused_under_a_month_end(self):
		for day in ("2030-01-28", "2030-01-31"):
			with self.subTest(start=day), self.assertRaises(frappe.ValidationError):
				self.rows("2030-01-01", "2030-12-31", day)

	def test_a_row_from_the_28th_is_kept_under_an_end_on_the_1st(self):
		self.assertEqual(self.rows("2030-01-01", "2031-01-01", "2030-01-28", "2030-02-28"), ("2030-02-28", 1))

	def test_an_end_inside_a_later_month_is_kept_from_the_1st(self):
		self.assertEqual(request_dates("2030-01-01", "2030-03-15"), ("2030-03-15", 2))

	def test_another_start_day_keeps_today_s_dates(self):
		# Today's rule: the end moves to the anniversary of the whole months
		self.assertEqual(request_dates("2030-12-12", "2031-02-20"), ("2031-02-12", 2))
		# A part month length without an end fails in add_months, as it does today
		with self.assertRaises(ValueError):
			request_dates("2030-01-15", None, 1.5)


class TestSchedules(FrappeTestCase):
	def periods(self, start, end):
		request = ScheduleRequest(
			start_date=frappe.utils.getdate(start),
			end_date=frappe.utils.getdate(end),
			base_rate=1000,
			rule=IncrementRule(interval_months=1, percentage=10),
		)
		return [(str(p.valid_from), str(p.valid_upto), p.rate) for p in build_schedule(request)]

	def test_a_month_end_gives_the_prices_of_the_anniversary(self):
		self.assertEqual(self.periods("2030-01-01", "2030-02-28"), self.periods("2030-01-01", "2030-03-01"))
		self.assertEqual(self.periods("2030-01-01", "2030-12-31"), self.periods("2030-01-01", "2031-01-01"))

	def test_another_start_day_keeps_its_prices(self):
		self.assertEqual(self.periods("2030-01-15", "2030-02-15"), [("2030-01-15", "2030-02-14", 1000.0)])
		self.assertEqual(self.periods("2030-01-15", "2030-02-14"), [("2030-01-15", "2030-02-14", 1000.0)])


class TestItemPrices(fx.SavepointMixin, FrappeTestCase):
	"""P1 on the anniversary form, P2 on the month end: the same Item Prices."""

	def setUp(self):
		super().setUp()
		fx.use_approach("Item Price")
		setup_items()

	def prices(self, start, end, property_name):
		request = make_request([(property_name, start, None)], start, end)
		item_price_actions.create_item_price_schedule(
			docname=request.name,
			properties=[property_name],
			base_rates={property_name: 1000},
			start_date=start,
			price_list=fx.PRICE_LIST,
			increment=INCREMENT,
		)
		rows = frappe.get_all(
			"Item Price",
			filters={"item_code": property_name, "price_list": fx.PRICE_LIST, "customer": fx.CUSTOMER},
			fields=["valid_from", "valid_upto", "price_list_rate"],
			order_by="valid_from asc",
		)
		billed = request_prices.last_billed_day(request, property_name)
		return [(str(r.valid_from), str(r.valid_upto), r.price_list_rate) for r in rows], str(billed)

	def test_a_year_to_31_december_matches_a_year_to_1_january(self):
		old = self.prices("2030-01-01", "2031-01-01", P1)
		new = self.prices("2030-01-01", "2030-12-31", P2)

		self.assertEqual(new, old)
		self.assertEqual((len(new[0]), new[0][-1][1], new[1]), (12, "2030-12-31", "2030-12-31"))

	def test_two_months_to_28_february_match_two_months_to_1_march(self):
		self.assertEqual(self.prices("2030-01-01", "2030-02-28", P2), self.prices("2030-01-01", "2030-03-01", P1))
