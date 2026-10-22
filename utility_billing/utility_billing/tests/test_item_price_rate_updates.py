"""Tests for manual rate corrections on the Item Price schedule.

The Update Prices action writes back to real ``Item Price`` records, so these
tests focus on what it is allowed to touch: the request's own items, only the
rate, and nothing else.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import flt

from utility_billing.utility_billing.tests import factories
from utility_billing.utility_billing.utils import item_price_actions
from utility_billing.utility_billing.utils import item_prices as item_price_utils
from utility_billing.utility_billing.utils.item_price_schedule import RatePeriod

TEST_ITEM = "_Test Rate Edit Item"
OTHER_ITEM = "_Test Rate Edit Other Item"
PROPERTY = "_Test Rate Edit Property"
OTHER_PROPERTY = "_Test Rate Edit Other Property"
CUSTOMER = "_Test Rate Edit Customer"
PRICE_LIST = "_Test Rate Edit Price List"


class TestItemPriceRateUpdates(FrappeTestCase):
	def setUp(self):
		self._enable_item_price_approach()
		factories.ensure_item(TEST_ITEM)
		factories.ensure_item(OTHER_ITEM)
		factories.ensure_price_list(PRICE_LIST)
		factories.ensure_property(PROPERTY, service_item=TEST_ITEM)
		factories.ensure_property(OTHER_PROPERTY, service_item=OTHER_ITEM)
		factories.ensure_customer(CUSTOMER)

		factories.delete_prices(TEST_ITEM, PRICE_LIST)
		factories.delete_prices(OTHER_ITEM, PRICE_LIST)

		self.service_request = self._create_request([PROPERTY])
		self.price = self._create_price(TEST_ITEM, 1000)

	def tearDown(self):
		factories.delete_prices(TEST_ITEM, PRICE_LIST)
		factories.delete_prices(OTHER_ITEM, PRICE_LIST)

	def _enable_item_price_approach(self):
		settings = frappe.get_doc("Utility Billing Settings", "Utility Billing Settings")
		settings.rent_billing_approach = "Item Price"
		settings.save(ignore_permissions=True)
		frappe.clear_cache(doctype="Utility Billing Settings")

	def _create_request(self, properties):
		request = frappe.new_doc("Utility Service Request")
		request.customer = CUSTOMER
		request.party_type = "Customer"
		request.party_name = CUSTOMER
		request.price_list = PRICE_LIST
		request.flags.ignore_mandatory = True
		request.flags.ignore_links = True

		# The controller requires at least one item on the request.
		request.append("items", {"item_code": TEST_ITEM, "qty": 1, "uom": "Nos"})

		for property_name in properties:
			request.append(
				"requested_properties",
				{"utility_property": property_name, "item_code": TEST_ITEM},
			)

		request.insert(ignore_permissions=True)

		return request

	def _create_price(self, item_code, rate, customer=None):
		"""Insert one Item Price for the given item and return its name."""
		return item_price_utils.insert_item_price(
			item_price_utils.ScheduleOptions(
				price_list=PRICE_LIST,
				start_date="2026-01-01",
				end_date="2026-12-31",
				uom="Nos",
				frequency="Yearly",
			),
			item_price_utils.ScheduleLine(
				item_code=item_code, customer=customer, base_rate=rate
			),
			RatePeriod(
				valid_from="2026-01-01",
				valid_upto="2026-12-31",
				rate=rate,
				increment_count=0,
			),
		)

	def _rate_of(self, name):
		return flt(frappe.db.get_value("Item Price", name, "price_list_rate"))

	def test_edited_rate_is_written_to_the_item_price(self):
		result = item_price_actions.update_item_price_rates(
			self.service_request.name,
			[{"name": self.price, "price_list_rate": 1250.5}],
		)

		self.assertEqual(result["updated"], 1)
		self.assertEqual(self._rate_of(self.price), 1250.5)

	def test_unchanged_rate_is_reported_and_not_written(self):
		before = frappe.db.get_value("Item Price", self.price, "modified")

		result = item_price_actions.update_item_price_rates(
			self.service_request.name,
			[{"name": self.price, "price_list_rate": 1000}],
		)

		self.assertEqual(result["updated"], 0)
		self.assertEqual(result["unchanged"], 1)
		self.assertEqual(frappe.db.get_value("Item Price", self.price, "modified"), before)

	def test_price_of_an_unrelated_item_is_rejected(self):
		foreign = self._create_price(OTHER_ITEM, 500)

		result = item_price_actions.update_item_price_rates(
			self.service_request.name,
			[{"name": foreign, "price_list_rate": 9999}],
		)

		self.assertEqual(result["updated"], 0)
		self.assertEqual(result["rejected"], 1)
		self.assertEqual(self._rate_of(foreign), 500)

	def test_unknown_price_name_is_rejected(self):
		result = item_price_actions.update_item_price_rates(
			self.service_request.name,
			[{"name": "IP-DOES-NOT-EXIST", "price_list_rate": 9999}],
		)

		self.assertEqual(result["updated"], 0)
		self.assertEqual(result["rejected"], 1)

	def test_dates_and_scope_of_the_price_are_untouched(self):
		item_price_actions.update_item_price_rates(
			self.service_request.name,
			[{"name": self.price, "price_list_rate": 1500}],
		)

		price = frappe.db.get_value(
			"Item Price",
			self.price,
			["item_code", "price_list", "valid_from", "valid_upto"],
			as_dict=True,
		)

		self.assertEqual(price.item_code, TEST_ITEM)
		self.assertEqual(price.price_list, PRICE_LIST)
		self.assertEqual(str(price.valid_from), "2026-01-01")
		self.assertEqual(str(price.valid_upto), "2026-12-31")

	def test_a_request_without_properties_edits_nothing(self):
		empty = self._create_request([])

		result = item_price_actions.update_item_price_rates(
			empty.name, [{"name": self.price, "price_list_rate": 9999}]
		)

		self.assertEqual(result["updated"], 0)
		self.assertEqual(result["rejected"], 1)
		self.assertEqual(self._rate_of(self.price), 1000)

	def test_negative_rate_is_rejected(self):
		self.assertRaises(
			frappe.ValidationError,
			item_price_actions.update_item_price_rates,
			self.service_request.name,
			[{"name": self.price, "price_list_rate": -50}],
		)

		self.assertEqual(self._rate_of(self.price), 1000)

	def test_summary_renders_editable_rate_inputs(self):
		summary = item_price_actions.get_item_price_summary(self.service_request.name)

		self.assertIn("uips-update-btn", summary["html"])
		self.assertIn(f'data-item-price="{self.price}"', summary["html"])
		self.assertIn('value="1000.00"', summary["html"])

	def test_summary_offers_the_editor_without_prices(self):
		"""A property can be given periods even before any price exists."""
		property_name = "_Test Rate Edit Bare Property"
		factories.ensure_property(property_name)
		frappe.db.set_value("Utility Property", property_name, "service_item", None)

		bare = self._create_request([property_name])

		summary = item_price_actions.get_item_price_summary(bare.name)

		self.assertFalse(summary["has_prices"])
		self.assertIn("uips-update-btn", summary["html"])
		self.assertIn("uips-add-row", summary["html"])

	def test_summary_is_read_only_when_rent_is_not_billed_by_item_price(self):
		settings = frappe.get_doc("Utility Billing Settings", "Utility Billing Settings")
		settings.rent_billing_approach = "Auto Repeat"
		settings.save(ignore_permissions=True)
		frappe.clear_cache(doctype="Utility Billing Settings")

		try:
			summary = item_price_actions.get_item_price_summary(self.service_request.name)

			self.assertNotIn("uips-update-btn", summary["html"])
			self.assertNotIn("uips-add-row", summary["html"])
		finally:
			self._enable_item_price_approach()
