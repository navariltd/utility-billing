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
TEST_PROPERTY = "_Test Rent Schedule Property"


class TestItemPriceCreation(FrappeTestCase):
	"""Creation and idempotency of generated Item Prices."""

	def setUp(self):
		super().setUp()
		factories.ensure_price_list(TEST_PRICE_LIST)
		factories.ensure_item(TEST_ITEM)

	def tearDown(self):
		factories.delete_prices(TEST_ITEM, TEST_PRICE_LIST)
		frappe.db.delete("Utility Service Request", {"price_list": TEST_PRICE_LIST})
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
				item_code=TEST_ITEM,
				customer=customer,
				base_rate=base_rate,
			)
		]

	def _create_request(self, customer=None, start_date="2026-01-01", end_date="2026-03-31"):
		"""Insert a draft request leasing the test property for one window.

		It owns its customer's prices of the property's service item that start
		between ``start_date`` and ``end_date``.
		"""
		factories.ensure_property(TEST_PROPERTY, service_item=TEST_ITEM)

		request = frappe.new_doc("Utility Service Request")
		request.service_request_from = "Customer"
		request.party_name = customer
		request.customer = customer
		request.company = frappe.db.get_value("Company", {}, "name")
		request.price_list = TEST_PRICE_LIST
		request.start_date = start_date
		request.append(
			"requested_properties",
			{
				"utility_property": TEST_PROPERTY,
				"start_date": start_date,
				"end_date": end_date,
				"is_active": 1,
			},
		)
		request.append("items", {"item_code": TEST_ITEM, "qty": 1, "rate": 1000})
		request.flags.ignore_mandatory = True
		request.flags.ignore_links = True
		request.insert(ignore_permissions=True)

		return request

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
		customer = self._ensure_customer()
		request = self._create_request(customer)

		item_price_utils.create_item_prices(self._options(), self._lines(customer=customer))

		item_by_property = {
			name: item
			for item, name in item_price_summary.get_property_item_codes(
				[TEST_PROPERTY]
			).items()
		}

		self.assertEqual(item_by_property.get(TEST_PROPERTY), TEST_ITEM)
		self.assertEqual(
			len(
				item_price_summary.get_created_prices(
					TEST_ITEM, request, TEST_PROPERTY, TEST_PRICE_LIST
				)
			),
			1,
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

	def test_delete_existing_schedule_removes_only_the_request_window(self):
		"""Deletion keeps to the request's customer and lease window."""
		customer = self._ensure_customer()
		other_customer = factories.ensure_customer("_Test Rent Schedule Other Customer")
		owner = self._create_request(customer)
		self._create_request(customer, start_date="2026-04-01", end_date="2026-06-30")

		item_price_utils.create_item_prices(self._options(), self._lines(customer=customer))
		item_price_utils.create_item_prices(
			self._options(start_date="2026-04-01", end_date="2026-06-30"),
			self._lines(customer=customer),
		)
		item_price_utils.create_item_prices(self._options(), self._lines(customer=other_customer))
		item_price_utils.create_item_prices(self._options(), self._lines())

		deleted = item_price_utils.delete_existing_schedule(owner, TEST_PRICE_LIST, {TEST_ITEM})

		self.assertEqual(deleted, 1)
		remaining = [
			(str(row.valid_from), row.customer)
			for row in frappe.get_all(
				"Item Price",
				filters={"item_code": TEST_ITEM, "price_list": TEST_PRICE_LIST},
				fields=["valid_from", "customer"],
			)
		]
		self.assertCountEqual(
			remaining,
			[("2026-04-01", customer), ("2026-01-01", other_customer), ("2026-01-01", None)],
		)

	def test_delete_existing_schedule_without_a_customer_deletes_nothing(self):
		item_price_utils.create_item_prices(self._options(), self._lines())

		deleted = item_price_utils.delete_existing_schedule(
			self._create_request(), TEST_PRICE_LIST, {TEST_ITEM}
		)

		self.assertEqual(deleted, 0)
		self.assertEqual(len(self._fetch_prices()), 1)

	def test_delete_existing_schedule_leaves_other_items_alone(self):
		other_item = "_Test Other Rent Item"
		factories.ensure_item(other_item)
		customer = self._ensure_customer()
		request = self._create_request(customer)

		try:
			item_price_utils.create_item_prices(self._options(), self._lines(customer=customer))

			other = frappe.new_doc("Item Price")
			other.item_code = other_item
			other.price_list = TEST_PRICE_LIST
			other.uom = "Nos"
			other.customer = customer
			other.price_list_rate = 7000
			other.valid_from = "2026-02-01"
			other.insert(ignore_permissions=True)

			item_price_utils.delete_existing_schedule(request, TEST_PRICE_LIST, {TEST_ITEM})

			self.assertTrue(frappe.db.exists("Item Price", other.name))
			self.assertEqual(self._fetch_prices(), [])
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
