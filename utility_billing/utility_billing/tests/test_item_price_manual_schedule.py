"""Tests for hand edited (manual) Item Price schedules.

Two layers are covered:

- ``build_manual_schedule`` enforces that a manual schedule covers the whole
  contract period. These tests are pure and need no database.
- The whitelisted actions accept a manual schedule, apply it verbatim and
  reject one that leaves part of the contract unpriced.
"""

from datetime import date

import frappe
from frappe.tests import UnitTestCase
from frappe.tests.utils import FrappeTestCase
from frappe.utils import getdate

from utility_billing.utility_billing.tests import factories
from utility_billing.utility_billing.utils import item_price_actions
from utility_billing.utility_billing.utils import item_prices as item_price_utils
from utility_billing.utility_billing.utils import item_price_summary_actions
from utility_billing.utility_billing.utils.item_price_schedule import RatePeriod
from utility_billing.utility_billing.utils.item_price_validation import (
	build_manual_schedule,
)

ITEM = "_Test Manual Item"
OTHER_ITEM = "_Test Manual Other Item"
PROPERTY = "_Test Manual Property"
PRICE_LIST = "_Test Manual Price List"
CUSTOMER = "_Test Manual Customer"

START = "2026-01-01"
END = "2027-01-01"


def period(valid_from, valid_upto, rate):
	"""Build a manual rate period."""
	return RatePeriod(
		valid_from=getdate(valid_from),
		valid_upto=getdate(valid_upto),
		rate=rate,
		increment_count=0,
	)


class TestManualScheduleValidation(UnitTestCase):
	"""Coverage rules of a hand edited schedule."""

	def test_a_single_period_covering_the_contract_is_valid(self):
		schedule = build_manual_schedule([period(START, END, 1000)], START, END)

		self.assertEqual(len(schedule), 1)
		self.assertEqual(schedule[0].valid_from, date(2026, 1, 1))
		self.assertEqual(schedule[0].valid_upto, date(2027, 1, 1))

	def test_periods_are_sorted_by_start_date(self):
		schedule = build_manual_schedule(
			[
				period("2026-07-01", END, 1200),
				period(START, "2026-06-30", 1000),
			],
			START,
			END,
		)

		self.assertEqual(schedule[0].rate, 1000)
		self.assertEqual(schedule[1].rate, 1200)

	def test_schedule_starting_after_the_contract_is_rejected(self):
		with self.assertRaises(ValueError):
			build_manual_schedule([period("2026-02-01", END, 1000)], START, END)

	def test_a_gap_between_periods_is_rejected(self):
		with self.assertRaises(ValueError):
			build_manual_schedule(
				[
					period(START, "2026-05-31", 1000),
					period("2026-07-01", END, 1000),
				],
				START,
				END,
			)

	def test_an_overlap_between_periods_is_rejected(self):
		with self.assertRaises(ValueError):
			build_manual_schedule(
				[
					period(START, "2026-06-30", 1000),
					period("2026-06-30", END, 1000),
				],
				START,
				END,
			)

	def test_schedule_stopping_before_the_contract_end_is_rejected(self):
		with self.assertRaises(ValueError):
			build_manual_schedule([period(START, "2026-06-30", 1000)], START, END)

	def test_open_ended_contract_only_needs_a_contiguous_schedule(self):
		schedule = build_manual_schedule(
			[period(START, "2027-06-30", 1000)], START, None
		)

		self.assertEqual(len(schedule), 1)

	def test_period_without_dates_is_rejected(self):
		with self.assertRaises(ValueError):
			build_manual_schedule([RatePeriod(None, None, 1000, 0)], START, END)

	def test_period_ending_before_it_starts_is_rejected(self):
		with self.assertRaises(ValueError):
			build_manual_schedule([period("2026-06-30", START, 1000)], START, END)

	def test_negative_rate_is_rejected(self):
		with self.assertRaises(ValueError):
			build_manual_schedule([period(START, END, -1)], START, END)

	def test_empty_schedule_is_rejected(self):
		with self.assertRaises(ValueError):
			build_manual_schedule([], START, END)


class TestManualSchedulePersistence(FrappeTestCase):
	"""Manual schedules as accepted by the whitelisted actions."""

	def setUp(self):
		super().setUp()
		self._enable_item_price_approach()
		factories.ensure_price_list(PRICE_LIST)
		factories.ensure_item(ITEM)
		factories.ensure_item(OTHER_ITEM)
		factories.ensure_property(PROPERTY, service_item=ITEM)
		factories.ensure_customer(CUSTOMER)
		self._clear_prices()
		self.service_request = self._create_request()

	def tearDown(self):
		self._clear_prices()
		frappe.db.delete("Utility Service Request", {"name": self.service_request.name})
		super().tearDown()

	def _enable_item_price_approach(self):
		settings = frappe.get_doc("Utility Billing Settings", "Utility Billing Settings")
		settings.rent_billing_approach = "Item Price"
		settings.save(ignore_permissions=True)
		frappe.clear_cache(doctype="Utility Billing Settings")

	def _clear_prices(self):
		item_price_utils.delete_existing_schedule(ITEM, PRICE_LIST)
		item_price_utils.delete_existing_schedule(OTHER_ITEM, PRICE_LIST)

	def _create_request(self):
		request = frappe.new_doc("Utility Service Request")
		request.customer = CUSTOMER
		request.company = frappe.db.get_value("Company", {}, "name")
		request.price_list = PRICE_LIST
		request.start_date = START
		request.end_date = END
		request.contract_length_months = 12
		request.append(
			"requested_properties",
			{
				"utility_property": PROPERTY,
				"start_date": START,
				"end_date": END,
				"is_active": 1,
			},
		)
		request.append("items", {"item_code": ITEM, "qty": 1, "rate": 1000})
		request.flags.ignore_mandatory = True
		request.flags.ignore_links = True
		request.insert(ignore_permissions=True)

		return request

	def _action_args(self, manual_periods):
		return {
			"docname": self.service_request.name,
			"properties": [PROPERTY],
			"base_rates": {},
			"start_date": START,
			"end_date": END,
			"price_list": PRICE_LIST,
			"manual_schedules": {PROPERTY: manual_periods},
		}

	def _prices(self):
		return frappe.get_all(
			"Item Price",
			filters={"item_code": ITEM, "price_list": PRICE_LIST},
			fields=["name", "valid_from", "valid_upto", "price_list_rate"],
			order_by="valid_from asc",
		)

	def _seed_single_price(self):
		item_price_actions.create_item_price_schedule(
			**self._action_args(
				[{"valid_from": START, "valid_upto": END, "rate": 1000}]
			)
		)

		return self._prices()[0]["name"]

	def test_create_uses_the_manual_periods_verbatim(self):
		result = item_price_actions.create_item_price_schedule(
			**self._action_args(
				[
					{"valid_from": START, "valid_upto": "2026-06-30", "rate": 1000},
					{"valid_from": "2026-07-01", "valid_upto": END, "rate": 1500},
				]
			)
		)

		self.assertEqual(result["created_count"], 2)
		self.assertEqual(
			[
				(str(row["valid_from"]), str(row["valid_upto"]), row["price_list_rate"])
				for row in self._prices()
			],
			[
				(START, "2026-06-30", 1000.0),
				("2026-07-01", END, 1500.0),
			],
		)

	def test_create_rejects_a_schedule_that_leaves_a_gap(self):
		with self.assertRaises(frappe.ValidationError):
			item_price_actions.create_item_price_schedule(
				**self._action_args(
					[{"valid_from": START, "valid_upto": "2026-06-30", "rate": 1000}]
				)
			)

		self.assertEqual(self._prices(), [])

	def test_preview_returns_the_manual_periods(self):
		preview = item_price_actions.preview_item_price_schedule(
			**self._action_args(
				[{"valid_from": START, "valid_upto": END, "rate": 1200}]
			)
		)

		self.assertEqual(len(preview), 1)
		self.assertEqual(len(preview[0]["periods"]), 1)
		self.assertEqual(preview[0]["periods"][0]["rate"], 1200)

	def test_saving_splits_a_period_by_adding_a_row(self):
		name = self._seed_single_price()

		result = item_price_summary_actions.save_item_price_schedule(
			self.service_request.name,
			{
				PROPERTY: {
					"periods": [
						{
							"name": name,
							"valid_from": START,
							"valid_upto": "2026-06-30",
							"price_list_rate": 1000,
						},
						{
							"valid_from": "2026-07-01",
							"valid_upto": END,
							"price_list_rate": 1500,
						},
					],
					"deleted": [],
				}
			},
		)

		self.assertEqual(result["updated"], 1)
		self.assertEqual(result["created"], 1)
		self.assertEqual(
			[(str(p["valid_from"]), str(p["valid_upto"])) for p in self._prices()],
			[(START, "2026-06-30"), ("2026-07-01", END)],
		)

	def test_saving_extends_one_period_and_removes_another(self):
		item_price_actions.create_item_price_schedule(
			**self._action_args(
				[
					{"valid_from": START, "valid_upto": "2026-06-30", "rate": 1000},
					{"valid_from": "2026-07-01", "valid_upto": END, "rate": 1500},
				]
			)
		)
		first, second = self._prices()

		result = item_price_summary_actions.save_item_price_schedule(
			self.service_request.name,
			{
				PROPERTY: {
					"periods": [
						{
							"name": first["name"],
							"valid_from": START,
							"valid_upto": END,
							"price_list_rate": 1200,
						}
					],
					"deleted": [second["name"]],
				}
			},
		)

		self.assertEqual(result["updated"], 1)
		self.assertEqual(result["deleted"], 1)
		prices = self._prices()
		self.assertEqual(len(prices), 1)
		self.assertEqual(str(prices[0]["valid_upto"]), END)
		self.assertEqual(prices[0]["price_list_rate"], 1200.0)

	def test_saving_an_incomplete_schedule_writes_nothing(self):
		name = self._seed_single_price()

		with self.assertRaises(frappe.ValidationError):
			item_price_summary_actions.save_item_price_schedule(
				self.service_request.name,
				{
					PROPERTY: {
						"periods": [
							{
								"name": name,
								"valid_from": START,
								"valid_upto": "2026-06-30",
								"price_list_rate": 9999,
							}
						],
						"deleted": [],
					}
				},
			)

		prices = self._prices()
		self.assertEqual(len(prices), 1)
		self.assertEqual(prices[0]["price_list_rate"], 1000.0)

	def test_saving_rejects_a_price_outside_the_request(self):
		foreign = item_price_utils.insert_item_price(
			item_price_utils.ScheduleOptions(
				price_list=PRICE_LIST,
				start_date=START,
				end_date=END,
				uom="Nos",
			),
			item_price_utils.ScheduleLine(
				item_code=OTHER_ITEM, customer=None, base_rate=1000
			),
			period(START, END, 1000),
		)

		try:
			result = item_price_summary_actions.save_item_price_schedule(
				self.service_request.name,
				{
					PROPERTY: {
						"periods": [
							{
								"name": foreign,
								"valid_from": START,
								"valid_upto": END,
								"price_list_rate": 9999,
							}
						],
						"deleted": [],
					}
				},
			)

			self.assertEqual(result["skipped"], 1)
			self.assertEqual(
				frappe.db.get_value("Item Price", foreign, "price_list_rate"), 1000.0
			)
		finally:
			frappe.delete_doc("Item Price", foreign, force=True, ignore_permissions=True)

	def test_saving_is_blocked_when_rent_is_not_billed_by_item_price(self):
		settings = frappe.get_doc("Utility Billing Settings", "Utility Billing Settings")
		settings.rent_billing_approach = "Auto Repeat"
		settings.save(ignore_permissions=True)
		frappe.clear_cache(doctype="Utility Billing Settings")

		try:
			with self.assertRaises(frappe.ValidationError):
				item_price_summary_actions.save_item_price_schedule(
					self.service_request.name,
					{PROPERTY: {"periods": [], "deleted": []}},
				)
		finally:
			self._enable_item_price_approach()
