"""Integration tests for generating Item Prices from a rent schedule.

These tests create real ``Item``, ``Price List`` and ``Item Price`` records so
that duplicate protection and idempotency of the schedule writer are verified
against the database.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import flt, getdate

from utility_billing.utility_billing.tests import factories
from utility_billing.utility_billing.utils import item_prices as item_price_utils
from utility_billing.utility_billing.utils import item_price_summary
from utility_billing.utility_billing.utils.item_price_schedule import IncrementRule
from utility_billing.utility_billing.utils.item_price_uom import (
	FALLBACK_UOM,
	resolve_uom,
	uom_exists,
	uom_valid_for_all,
)

TEST_ITEM = "_Test Rent Schedule Item"
TEST_PRICE_LIST = "_Test Rent Schedule Price List"


class TestItemPriceCreation(FrappeTestCase):
	"""Creation and idempotency of generated Item Prices."""

	def setUp(self):
		super().setUp()
		factories.ensure_price_list(TEST_PRICE_LIST)
		factories.ensure_item(TEST_ITEM)

	def tearDown(self):
		factories.delete_prices(TEST_ITEM, TEST_PRICE_LIST)
		super().tearDown()

	def _options(self, **overrides):
		defaults = {
			"price_list": TEST_PRICE_LIST,
			"start_date": "2026-01-01",
			"end_date": "2026-03-31",
			"uom": "Nos",
			"frequency": "Monthly",
			"rule": IncrementRule(interval_months=12, percentage=5),
		}
		defaults.update(overrides)

		return item_price_utils.ScheduleOptions(**defaults)

	def _lines(self, base_rate=1000, customer=None):
		return [
			item_price_utils.ScheduleLine(
				item_code=TEST_ITEM, customer=customer, base_rate=base_rate
			)
		]

	def _fetch_prices(self):
		return frappe.get_all(
			"Item Price",
			filters={"item_code": TEST_ITEM, "price_list": TEST_PRICE_LIST},
			fields=["name", "price_list_rate", "valid_from", "valid_upto", "customer"],
			order_by="valid_from asc",
		)

	def test_creates_one_price_per_rate_change(self):
		result = item_price_utils.create_item_prices(self._options(), self._lines())

		# A 3 month lease with a 12 month increment has one unchanging rate, so
		# a single Item Price covers the whole lease.
		self.assertEqual(result["created_count"], 1)
		self.assertEqual(result["skipped"], 0)

		prices = self._fetch_prices()
		self.assertEqual(len(prices), 1)
		self.assertEqual(getdate(prices[0]["valid_from"]), getdate("2026-01-01"))
		self.assertEqual(getdate(prices[0]["valid_upto"]), getdate("2026-03-31"))
		self.assertEqual(flt(prices[0]["price_list_rate"]), 1000)

	def test_merging_splits_only_where_the_rate_changes(self):
		options = self._options(
			end_date="2027-03-31", rule=IncrementRule(interval_months=12, percentage=10)
		)
		item_price_utils.create_item_prices(options, self._lines(base_rate=1000))

		prices = self._fetch_prices()
		self.assertEqual(len(prices), 2)

		self.assertEqual(getdate(prices[0]["valid_from"]), getdate("2026-01-01"))
		self.assertEqual(getdate(prices[0]["valid_upto"]), getdate("2026-12-31"))
		self.assertEqual(flt(prices[0]["price_list_rate"]), 1000)

		self.assertEqual(getdate(prices[1]["valid_from"]), getdate("2027-01-01"))
		self.assertEqual(getdate(prices[1]["valid_upto"]), getdate("2027-03-31"))
		self.assertEqual(flt(prices[1]["price_list_rate"]), 1100)

	def test_prices_are_grouped_back_to_the_property_by_item(self):
		"""The summary attributes prices to a property via its service item."""
		property_name = "_Test Grouped Property"
		factories.ensure_property(property_name, service_item=TEST_ITEM)

		item_price_utils.create_item_prices(self._options(), self._lines())

		item_by_property = {
			name: item
			for item, name in item_price_summary.get_property_item_codes(
				[property_name]
			).items()
		}

		self.assertEqual(item_by_property.get(property_name), TEST_ITEM)
		self.assertEqual(
			len(item_price_summary.get_created_prices(TEST_ITEM, TEST_PRICE_LIST)), 1
		)

	def test_rerunning_the_same_schedule_creates_no_duplicates(self):
		item_price_utils.create_item_prices(self._options(), self._lines())
		result = item_price_utils.create_item_prices(self._options(), self._lines())

		self.assertEqual(result["created_count"], 0)
		self.assertEqual(result["skipped"], 1)
		self.assertEqual(len(self._fetch_prices()), 1)

	def test_customer_specific_prices_do_not_collide_with_generic_ones(self):
		customer = self._ensure_customer()

		item_price_utils.create_item_prices(self._options(), self._lines())
		result = item_price_utils.create_item_prices(
			self._options(), self._lines(customer=customer)
		)

		self.assertEqual(result["created_count"], 1)
		self.assertEqual(len(self._fetch_prices()), 2)

	def test_increment_is_applied_to_later_periods(self):
		options = self._options(
			end_date="2027-03-31", rule=IncrementRule(interval_months=12, percentage=10)
		)
		item_price_utils.create_item_prices(options, self._lines(base_rate=1000))

		prices = self._fetch_prices()
		self.assertEqual(len(prices), 2)
		self.assertEqual(flt(prices[0]["price_list_rate"]), 1000)
		self.assertEqual(flt(prices[-1]["price_list_rate"]), 1100)

	def test_created_prices_are_plain_item_prices(self):
		item_price_utils.create_item_prices(self._options(), self._lines())

		prices = frappe.get_all(
			"Item Price",
			filters={"item_code": TEST_ITEM, "price_list": TEST_PRICE_LIST},
			fields=["item_code", "customer", "price_list_rate", "valid_from", "valid_upto"],
		)

		self.assertEqual(len(prices), 1)
		self.assertEqual(prices[0]["item_code"], TEST_ITEM)
		self.assertEqual(prices[0]["customer"], None)

	def test_delete_existing_schedule_removes_all_prices_of_the_item(self):
		"""Deletion scopes to one item, price list and customer."""
		item_price_utils.create_item_prices(self._options(), self._lines())

		manual = frappe.new_doc("Item Price")
		manual.item_code = TEST_ITEM
		manual.price_list = TEST_PRICE_LIST
		manual.uom = "Nos"
		manual.price_list_rate = 5000
		manual.valid_from = "2030-01-01"
		manual.insert(ignore_permissions=True)

		deleted = item_price_utils.delete_existing_schedule(TEST_ITEM, TEST_PRICE_LIST)

		self.assertEqual(deleted, 2)
		self.assertEqual(len(self._fetch_prices()), 0)

	def test_delete_existing_schedule_leaves_other_items_alone(self):
		other_item = "_Test Other Rent Item"
		factories.ensure_item(other_item)

		try:
			item_price_utils.create_item_prices(self._options(), self._lines())

			other = frappe.new_doc("Item Price")
			other.item_code = other_item
			other.price_list = TEST_PRICE_LIST
			other.uom = "Nos"
			other.price_list_rate = 7000
			other.valid_from = "2030-01-01"
			other.insert(ignore_permissions=True)

			item_price_utils.delete_existing_schedule(TEST_ITEM, TEST_PRICE_LIST)

			self.assertTrue(frappe.db.exists("Item Price", other.name))
		finally:
			factories.delete_prices(other_item, TEST_PRICE_LIST)

	def test_creating_prices_for_an_adjacent_period_is_allowed(self):
		item_price_utils.create_item_prices(self._options(), self._lines())

		adjacent = self._options(start_date="2026-04-01", end_date="2026-06-30")
		result = item_price_utils.create_item_prices(adjacent, self._lines())

		self.assertEqual(result["created_count"], 1)
		self.assertEqual(len(self._fetch_prices()), 2)

	def _ensure_customer(self):
		return factories.ensure_customer("_Test Rent Schedule Customer")


class TestItemPriceUomResolution(FrappeTestCase):
	"""A UOM is only used when the items being priced actually support it."""

	def setUp(self):
		super().setUp()
		self.item_code = "_Test UOM Rent Item"
		factories.ensure_item(self.item_code, stock_uom=FALLBACK_UOM)

	def tearDown(self):
		frappe.db.delete("Item", {"item_code": self.item_code})
		super().tearDown()

	def test_configured_uom_is_used_when_valid_for_the_item(self):
		settings = frappe._dict({"default_item_price_uom": FALLBACK_UOM})

		self.assertEqual(resolve_uom(settings, [self.item_code]), FALLBACK_UOM)

	def test_blank_configured_uom_resolves_from_the_item(self):
		settings = frappe._dict({"default_item_price_uom": None})

		self.assertEqual(resolve_uom(settings, [self.item_code]), FALLBACK_UOM)

	def test_invalid_configured_uom_is_not_accepted(self):
		self.assertFalse(uom_valid_for_all("_No Such UOM", [self.item_code]))
		self.assertFalse(uom_exists("_No Such UOM"))
