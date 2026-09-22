"""Tests for resolving an item rate on a given date.

Rent and utility items are priced per period, so the rate of an invoice line
depends on the date it is billed for: the rate of a date follows the Item Price
valid then, preferring the price scoped to the customer and the price list of
the document.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, flt, today

from utility_billing.api.sales_invoice import get_line_rate
from utility_billing.utility_billing.tests import factories
from utility_billing.utility_billing.utils.item_rate import get_rate_for_date

TEST_ITEM = "_Test Rate On Date Item"
TEST_CUSTOMER = "_Test Rate On Date Customer"
TEST_PRICE_LIST = "_Test Rate On Date Price List"
EARLIER_RATE = 100.0
LATER_RATE = 200.0
BASE_RATE = 150.0
CUSTOMER_RATE = 175.0


class TestItemRateForDate(FrappeTestCase):
	"""Rates resolved for a date."""

	def setUp(self):
		super().setUp()
		self.item = factories.ensure_item(TEST_ITEM)
		self.customer = factories.ensure_customer(TEST_CUSTOMER)
		self.price_list = factories.ensure_price_list(TEST_PRICE_LIST)
		self.uom = frappe.db.get_value("Item", self.item, "stock_uom")
		self.today = today()
		factories.delete_prices(self.item, self.price_list)

	def tearDown(self):
		factories.delete_prices(self.item, self.price_list)
		super().tearDown()

	def test_rate_of_the_period_of_the_date_is_returned(self):
		self._make_price(EARLIER_RATE, valid_upto=add_days(self.today, 10))
		self._make_price(LATER_RATE, valid_from=add_days(self.today, 11))

		self.assertEqual(flt(self._rate(self.today)), EARLIER_RATE)
		self.assertEqual(flt(self._rate(add_days(self.today, 30))), LATER_RATE)

	def test_customer_price_wins_over_the_general_price(self):
		self._make_price(BASE_RATE)
		self._make_price(CUSTOMER_RATE, customer=self.customer)

		self.assertEqual(flt(self._rate(self.today, customer=self.customer)), CUSTOMER_RATE)
		self.assertEqual(flt(self._rate(self.today)), BASE_RATE)

	def test_price_list_of_the_customer_is_used_when_none_is_given(self):
		frappe.db.set_value("Customer", self.customer, "default_price_list", self.price_list)
		self._make_price(BASE_RATE)

		rate = self._rate(self.today, customer=self.customer, use_line_price_list=False)

		self.assertEqual(flt(rate), BASE_RATE)

	def test_item_without_price_has_no_rate(self):
		self.assertIsNone(self._rate(self.today))
		self.assertIsNone(
			get_rate_for_date("_Test Rate On Date Unknown Item", self.today, price_list=self.price_list)
		)

	def test_line_rate_api_returns_the_rate_of_the_date(self):
		self._make_price(LATER_RATE, valid_from=add_days(self.today, 11))

		rate = get_line_rate(
			item_code=self.item,
			posting_date=add_days(self.today, 30),
			price_list=self.price_list,
			uom=self.uom,
			qty=1,
		)

		self.assertEqual(flt(rate), LATER_RATE)

	def _rate(self, posting_date, customer=None, use_line_price_list=True):
		"""Return the rate of the test item on a date."""
		return get_rate_for_date(
			self.item,
			posting_date,
			customer=customer,
			price_list=self.price_list if use_line_price_list else None,
			uom=self.uom,
			qty=1,
		)

	def _make_price(self, rate, valid_from=None, valid_upto=None, customer=None):
		"""Create an Item Price of the test item for the test price list."""
		price = frappe.new_doc("Item Price")
		price.flags.ignore_permissions = True
		price.item_code = self.item
		price.price_list = self.price_list
		price.uom = self.uom
		price.customer = customer
		price.price_list_rate = rate
		price.valid_from = valid_from or self.today
		price.valid_upto = valid_upto
		price.insert()
