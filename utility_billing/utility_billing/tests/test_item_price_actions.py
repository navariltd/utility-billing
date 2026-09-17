"""Integration tests for the Define Item Prices action of the service request.

Creates a minimal Utility Service Request with one property and verifies that
the action previews a schedule and creates the matching Item Prices, and that
re-running it stays idempotent.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import flt, getdate
from datetime import timedelta

from utility_billing.utility_billing.tests import factories
from utility_billing.utility_billing.utils import item_price_actions

TEST_ITEM = "_Test Action Rent Item"
TEST_PRICE_LIST = "_Test Action Rent Price List"
TEST_PROPERTY = "_Test Action Rent Property"
TEST_CUSTOMER = "_Test Rent Action Customer"
SECOND_ITEM = "_Test Action Rent Item 2"
SECOND_PROPERTY = "_Test Action Rent Property 2"


class TestItemPriceScheduleActions(FrappeTestCase):
	"""Preview and creation through the whitelisted action."""

	def setUp(self):
		super().setUp()
		self._enable_item_price_approach()
		factories.ensure_price_list(TEST_PRICE_LIST)
		factories.ensure_item(TEST_ITEM)
		factories.ensure_property(TEST_PROPERTY, service_item=TEST_ITEM)
		factories.ensure_customer(TEST_CUSTOMER)
		self.service_request = self._make_service_request()

	def tearDown(self):
		factories.delete_prices(TEST_ITEM, TEST_PRICE_LIST)
		factories.delete_prices(SECOND_ITEM, TEST_PRICE_LIST)
		frappe.db.delete("Utility Service Request", {"name": self.service_request.name})
		super().tearDown()

	def _enable_item_price_approach(self):
		settings = frappe.get_doc("Utility Billing Settings", "Utility Billing Settings")
		settings.rent_billing_approach = "Item Price"
		settings.save(ignore_permissions=True)
		frappe.clear_cache(doctype="Utility Billing Settings")

	def _make_service_request(self):
		service_request = frappe.new_doc("Utility Service Request")
		service_request.customer = TEST_CUSTOMER
		service_request.company = frappe.db.get_value("Company", {}, "name")
		service_request.price_list = TEST_PRICE_LIST
		service_request.start_date = "2026-01-01"
		service_request.end_date = "2027-01-01"
		service_request.contract_length_months = 12
		service_request.append(
			"requested_properties",
			{
				"utility_property": TEST_PROPERTY,
				"start_date": "2026-01-01",
				"end_date": "2027-01-01",
				"is_active": 1,
			},
		)
		service_request.append(
			"items",
			{
				"item_code": TEST_ITEM,
				"qty": 1,
				"rate": 1000,
				"utility_property": TEST_PROPERTY,
			},
		)
		service_request.flags.ignore_mandatory = True
		service_request.flags.ignore_links = True
		service_request.insert(ignore_permissions=True)

		return service_request


	def _action_args(self):
		return {
			"docname": self.service_request.name,
			"properties": frappe.as_json([TEST_PROPERTY]),
			"base_rates": frappe.as_json({TEST_PROPERTY: 1000}),
			"start_date": "2026-01-01",
			"end_date": "2026-12-31",
			"price_list": TEST_PRICE_LIST,
		}

	def test_preview_merges_periods_that_share_a_rate(self):
		# No increment is configured, so every month has the same rate and a
		# single Item Price should cover the whole lease.
		preview = item_price_actions.preview_item_price_schedule(**self._action_args())

		self.assertEqual(len(preview), 1)
		self.assertEqual(preview[0]["property"], TEST_PROPERTY)
		self.assertEqual(len(preview[0]["periods"]), 1)

		period = preview[0]["periods"][0]
		self.assertEqual(period["valid_from"], "2026-01-01")
		self.assertEqual(period["valid_upto"], "2026-12-31")
		self.assertEqual(flt(period["rate"]), 1000)

	def test_creating_a_schedule_creates_one_price_per_rate_change(self):
		result = item_price_actions.create_item_price_schedule(**self._action_args())

		self.assertEqual(result["created_count"], 1)
		self.assertEqual(result["skipped"], 0)

		prices = frappe.get_all(
			"Item Price",
			filters={"item_code": TEST_ITEM, "price_list": TEST_PRICE_LIST},
			fields=["valid_from", "valid_upto", "price_list_rate", "item_code", "customer"],
		)

		self.assertEqual(len(prices), 1)
		self.assertEqual(str(prices[0]["valid_from"]), "2026-01-01")
		self.assertEqual(str(prices[0]["valid_upto"]), "2026-12-31")
		self.assertEqual(prices[0]["item_code"], TEST_ITEM)

	def test_rerunning_the_action_skips_existing_periods(self):
		item_price_actions.create_item_price_schedule(**self._action_args())
		result = item_price_actions.create_item_price_schedule(**self._action_args())

		self.assertEqual(result["created_count"], 0)
		self.assertEqual(result["skipped"], 1)

	def test_increment_rule_increases_later_periods(self):
		rule_name = "_Test Action Increment Rule"
		frappe.db.delete("Billing Adjustment Rule", {"name": rule_name})

		rule = frappe.new_doc("Billing Adjustment Rule")
		rule.rule_name = rule_name
		rule.frequency = "Monthly"
		rule.increment_interval_months = 12
		rule.increment_percentage = 5
		rule.flags.ignore_mandatory = True
		rule.insert(ignore_permissions=True)

		try:
			args = self._action_args()
			args["adjustment_rule"] = rule_name
			args["end_date"] = "2027-12-31"
			result = item_price_actions.create_item_price_schedule(**args)

			periods = sorted(
				result["schedule"][0]["periods"], key=lambda row: row["valid_from"]
			)
			# Two yearly rates, so two merged periods covering a whole year each.
			self.assertEqual(len(periods), 2)
			self.assertEqual(getdate(periods[0]["valid_from"]), getdate("2026-01-01"))
			self.assertEqual(getdate(periods[0]["valid_upto"]), getdate("2026-12-31"))
			self.assertEqual(flt(periods[0]["rate"]), 1000)
			self.assertEqual(getdate(periods[1]["valid_from"]), getdate("2027-01-01"))
			self.assertEqual(getdate(periods[1]["valid_upto"]), getdate("2027-12-31"))
			self.assertEqual(flt(periods[1]["rate"]), 1050)
		finally:
			frappe.db.delete("Billing Adjustment Rule", {"name": rule_name})

	def test_missing_base_rate_is_rejected(self):
		args = self._action_args()
		args["base_rates"] = frappe.as_json({})

		with self.assertRaises(frappe.ValidationError):
			item_price_actions.preview_item_price_schedule(**args)

	def test_manual_override_replaces_generated_rate(self):
		args = self._action_args()
		args["overrides"] = frappe.as_json([{"from_date": "2026-07-01", "rate": 5000}])

		result = item_price_actions.create_item_price_schedule(**args)

		periods = sorted(result["schedule"][0]["periods"], key=lambda p: p["valid_from"])

		# The override splits the lease in two merged periods.
		self.assertEqual(len(periods), 2)
		self.assertEqual(getdate(periods[0]["valid_from"]), getdate("2026-01-01"))
		self.assertEqual(getdate(periods[0]["valid_upto"]), getdate("2026-06-30"))
		self.assertEqual(flt(periods[0]["rate"]), 1000)
		self.assertEqual(getdate(periods[1]["valid_from"]), getdate("2026-07-01"))
		self.assertEqual(getdate(periods[1]["valid_upto"]), getdate("2026-12-31"))
		self.assertEqual(flt(periods[1]["rate"]), 5000)

	def test_manual_increment_values_are_used_without_a_rule(self):
		args = self._action_args()
		args["end_date"] = "2027-12-31"
		args["adjustment_rule"] = None
		args["increment"] = frappe.as_json(
			{
				"interval_months": 12,
				"percentage": 10,
				"effective_after_months": 0,
				"basis": "Original Amount",
			}
		)

		result = item_price_actions.create_item_price_schedule(**args)

		periods = sorted(result["schedule"][0]["periods"], key=lambda p: p["valid_from"])
		self.assertEqual(len(periods), 2)
		self.assertEqual(flt(periods[0]["rate"]), 1000)
		self.assertEqual(getdate(periods[0]["valid_upto"]), getdate("2026-12-31"))
		self.assertEqual(flt(periods[1]["rate"]), 1100)
		self.assertEqual(getdate(periods[1]["valid_from"]), getdate("2027-01-01"))
		self.assertEqual(getdate(periods[1]["valid_upto"]), getdate("2027-12-31"))

	def test_manual_increment_overrides_the_rule_values(self):
		rule_name = "_Test Manual Increment Rule"
		frappe.db.delete("Billing Adjustment Rule", {"name": rule_name})

		rule = frappe.new_doc("Billing Adjustment Rule")
		rule.rule_name = rule_name
		rule.frequency = "Monthly"
		rule.increment_interval_months = 12
		rule.increment_percentage = 5
		rule.adjustment_basis = "Original Amount"
		rule.flags.ignore_mandatory = True
		rule.insert(ignore_permissions=True)

		try:
			args = self._action_args()
			args["end_date"] = "2027-12-31"
			args["adjustment_rule"] = rule_name
			# The rule says 5%; the modal says 20%.
			args["increment"] = frappe.as_json({"percentage": 20})
			result = item_price_actions.create_item_price_schedule(**args)

			periods = sorted(
				result["schedule"][0]["periods"], key=lambda p: p["valid_from"]
			)
			# The manual 20% wins over the rule's 5%.
			self.assertEqual(len(periods), 2)
			self.assertEqual(flt(periods[0]["rate"]), 1000)
			self.assertEqual(flt(periods[1]["rate"]), 1200)
			self.assertEqual(getdate(periods[1]["valid_from"]), getdate("2027-01-01"))
		finally:
			frappe.db.delete("Billing Adjustment Rule", {"name": rule_name})

	def test_five_year_lease_with_manual_five_percent_yearly_increment(self):
		args = self._action_args()
		args["end_date"] = "2031-01-01"
		args["adjustment_rule"] = None
		args["increment"] = frappe.as_json(
			{
				"interval_months": 12,
				"percentage": 5,
				"effective_after_months": 0,
				"basis": "Original Amount",
			}
		)

		result = item_price_actions.preview_item_price_schedule(**args)

		periods = sorted(result[0]["periods"], key=lambda p: p["valid_from"])

		# One merged period per year, each covering a full year.
		self.assertEqual(len(periods), 6)
		self.assertEqual(
			[
				(str(p["valid_from"]), str(p["valid_upto"]), flt(p["rate"]))
				for p in periods
			],
			[
				("2026-01-01", "2026-12-31", 1000),
				("2027-01-01", "2027-12-31", 1050),
				("2028-01-01", "2028-12-31", 1100),
				("2029-01-01", "2029-12-31", 1150),
				("2030-01-01", "2030-12-31", 1200),
				("2031-01-01", "2031-01-01", 1250),
			],
		)

	def test_five_year_lease_with_compounding_basis(self):
		args = self._action_args()
		args["end_date"] = "2031-01-01"
		args["adjustment_rule"] = None
		args["increment"] = frappe.as_json(
			{
				"interval_months": 12,
				"percentage": 5,
				"effective_after_months": 0,
				"basis": "Last Adjusted Amount",
			}
		)

		result = item_price_actions.preview_item_price_schedule(**args)

		periods = sorted(result[0]["periods"], key=lambda p: p["valid_from"])
		rates = [flt(period["rate"]) for period in periods]

		self.assertEqual(len(periods), 6)
		self.assertEqual(rates[0], 1000)
		self.assertEqual(rates[1], 1050)
		self.assertAlmostEqual(rates[2], 1102.5, places=4)
		self.assertAlmostEqual(rates[3], 1157.625, places=4)
		self.assertAlmostEqual(rates[4], 1215.50625, places=4)

	def test_annual_increment_with_effective_after_delay(self):
		args = self._action_args()
		args["end_date"] = "2029-01-01"
		args["adjustment_rule"] = None
		args["increment"] = frappe.as_json(
			{
				"interval_months": 12,
				"percentage": 5,
				"effective_after_months": 12,
				"basis": "Original Amount",
			}
		)

		result = item_price_actions.preview_item_price_schedule(**args)

		periods = sorted(result[0]["periods"], key=lambda p: p["valid_from"])

		# The first increment only applies 12 + 12 = 24 months after the start,
		# so the first two years share one rate and merge into one period.
		self.assertEqual(
			[
				(str(p["valid_from"]), str(p["valid_upto"]), flt(p["rate"]))
				for p in periods
			],
			[
				("2026-01-01", "2027-12-31", 1000),
				("2028-01-01", "2028-12-31", 1050),
				("2029-01-01", "2029-01-01", 1100),
			],
		)

		rule_name = "_Test Compounding Rule"
		frappe.db.delete("Billing Adjustment Rule", {"name": rule_name})

		rule = frappe.new_doc("Billing Adjustment Rule")
		rule.rule_name = rule_name
		rule.frequency = "Monthly"
		rule.increment_interval_months = 12
		rule.increment_percentage = 10
		rule.adjustment_basis = "Last Adjusted Amount"
		rule.flags.ignore_mandatory = True
		rule.insert(ignore_permissions=True)

		try:
			args = self._action_args()
			args["end_date"] = "2028-12-31"
			args["adjustment_rule"] = rule_name
			result = item_price_actions.create_item_price_schedule(**args)

			periods = sorted(
				result["schedule"][0]["periods"], key=lambda p: p["valid_from"]
			)
			# One merged period per year: 3 yearly rates over a 3 year lease.
			self.assertEqual(len(periods), 3)
			self.assertEqual(flt(periods[0]["rate"]), 1000)
			self.assertEqual(flt(periods[1]["rate"]), 1100)
			# Compounding introduces floating point noise, so use a delta.
			self.assertAlmostEqual(flt(periods[2]["rate"]), 1210, places=4)
		finally:
			frappe.db.delete("Billing Adjustment Rule", {"name": rule_name})

	def test_each_property_is_priced_with_its_own_starting_rate(self):
		second_property = self._ensure_second_property()

		first = self._action_args()
		first["base_rates"] = frappe.as_json({TEST_PROPERTY: 1000})
		item_price_actions.create_item_price_schedule(**first)

		second = self._action_args()
		second["properties"] = frappe.as_json([second_property])
		second["base_rates"] = frappe.as_json({second_property: 2500})
		second["adjustment_rule"] = None
		result = item_price_actions.create_item_price_schedule(**second)

		self.assertEqual(result["created_count"], 1)
		self.assertEqual(result["skipped"], 0)
		self.assertEqual(len(result["schedule"]), 1)
		self.assertEqual(result["schedule"][0]["property"], second_property)
		self.assertEqual(result["schedule"][0]["item_code"], self._second_item)
		self.assertEqual(flt(result["schedule"][0]["base_rate"]), 2500)
		self.assertTrue(
			all(flt(period["rate"]) == 2500 for period in result["schedule"][0]["periods"])
		)

	def test_preview_periods_match_the_table_columns(self):
		"""The modal maps these keys straight onto the Rates table columns."""
		args = self._action_args()
		args["end_date"] = "2027-12-31"
		args["adjustment_rule"] = None
		args["increment"] = frappe.as_json(
			{"interval_months": 12, "percentage": 10, "effective_after_months": 0}
		)

		preview = item_price_actions.preview_item_price_schedule(**args)

		self.assertEqual(len(preview[0]["periods"]), 2)

		for period in preview[0]["periods"]:
			# Every column of the Rates table resolves from these keys.
			self.assertTrue(period["valid_from"])
			self.assertTrue(period["valid_upto"])
			self.assertIn("rate", period)
			self.assertIn("increment_count", period)
			# Dates must be storage-format strings for the grid Date cells.
			self.assertRegex(period["valid_from"], r"^\d{4}-\d{2}-\d{2}$")
			self.assertRegex(period["valid_upto"], r"^\d{4}-\d{2}-\d{2}$")

	def test_preview_works_without_a_price_list(self):
		args = self._action_args()
		args["price_list"] = None
		self.service_request.price_list = None
		self.service_request.flags.ignore_mandatory = True
		self.service_request.flags.ignore_links = True
		self.service_request.save(ignore_permissions=True)

		preview = item_price_actions.preview_item_price_schedule(**args)

		self.assertEqual(len(preview), 1)
		self.assertEqual(len(preview[0]["periods"]), 1)
		self.assertEqual(preview[0]["periods"][0]["valid_from"], "2026-01-01")

	def test_creating_still_requires_a_price_list(self):
		args = self._action_args()
		args["price_list"] = None
		self.service_request.price_list = None
		self.service_request.flags.ignore_mandatory = True
		self.service_request.flags.ignore_links = True
		self.service_request.save(ignore_permissions=True)

		with self.assertRaises(frappe.ValidationError):
			item_price_actions.create_item_price_schedule(**args)

	def test_preview_returns_every_field_the_table_needs(self):
		preview = item_price_actions.preview_item_price_schedule(**self._action_args())

		period = preview[0]["periods"][0]

		# The modal builds its rows straight from these keys.
		for key in ("valid_from", "valid_upto", "rate", "increment_count"):
			self.assertIn(key, period)

		self.assertEqual(preview[0]["property"], TEST_PROPERTY)
		self.assertEqual(preview[0]["item_code"], TEST_ITEM)
		self.assertIsInstance(period["valid_from"], str)
		self.assertIsInstance(period["valid_upto"], str)

	def test_preview_only_returns_the_selected_property(self):
		self._ensure_second_property()

		args = self._action_args()
		args["properties"] = frappe.as_json([TEST_PROPERTY])

		result = item_price_actions.preview_item_price_schedule(**args)

		self.assertEqual(len(result), 1)
		self.assertEqual(result[0]["property"], TEST_PROPERTY)
		self.assertEqual(flt(result[0]["base_rate"]), 1000)

	def test_full_lease_creates_one_price_per_year_not_per_month(self):
		"""A 5 year lease with a yearly increment yields one price per year."""
		args = self._action_args()
		args["end_date"] = "2031-01-01"
		args["adjustment_rule"] = None
		args["customer"] = TEST_CUSTOMER
		args["increment"] = frappe.as_json(
			{
				"interval_months": 12,
				"percentage": 5,
				"effective_after_months": 0,
				"basis": "Original Amount",
			}
		)

		result = item_price_actions.create_item_price_schedule(**args)

		self.assertEqual(result["created_count"], 6)

		prices = frappe.get_all(
			"Item Price",
			filters={"item_code": TEST_ITEM, "price_list": TEST_PRICE_LIST},
			fields=[
				"valid_from",
				"valid_upto",
				"price_list_rate",
				"customer",
				"item_code",
			],
			order_by="valid_from asc",
		)

		self.assertEqual(len(prices), 6)

		self.assertEqual(
			[(str(p["valid_from"]), str(p["valid_upto"]), flt(p["price_list_rate"])) for p in prices],
			[
				("2026-01-01", "2026-12-31", 1000),
				("2027-01-01", "2027-12-31", 1050),
				("2028-01-01", "2028-12-31", 1100),
				("2029-01-01", "2029-12-31", 1150),
				("2030-01-01", "2030-12-31", 1200),
				("2031-01-01", "2031-01-01", 1250),
			],
		)

		# Each price is an ordinary Item Price for the property's service item.
		for price in prices:
			self.assertEqual(price["item_code"], TEST_ITEM)
			self.assertEqual(price["customer"], TEST_CUSTOMER)

	def test_schedule_is_contiguous_across_created_prices(self):
		args = self._action_args()
		args["end_date"] = "2029-01-01"
		args["adjustment_rule"] = None

		item_price_actions.create_item_price_schedule(**args)

		prices = frappe.get_all(
			"Item Price",
			filters={"item_code": TEST_ITEM, "price_list": TEST_PRICE_LIST},
			fields=["valid_from", "valid_upto"],
			order_by="valid_from asc",
		)

		self.assertEqual(str(prices[0]["valid_from"]), "2026-01-01")
		self.assertEqual(str(prices[-1]["valid_upto"]), "2029-01-01")

		for previous, current in zip(prices, prices[1:]):
			self.assertEqual(
				str(current["valid_from"]),
				str(getdate(previous["valid_upto"]) + timedelta(days=1)),
			)

	def test_summary_lists_the_created_prices_for_the_property(self):
		args = self._action_args()
		args["end_date"] = "2027-12-31"
		args["adjustment_rule"] = None

		item_price_actions.create_item_price_schedule(**args)

		summary = item_price_actions.get_item_price_summary(self.service_request.name)

		self.assertTrue(summary["has_prices"])
		self.assertIn(TEST_PROPERTY, summary["html"])
		self.assertIn(TEST_ITEM, summary["html"])
		self.assertIn("period(s)", summary["html"])

		self._ensure_second_property()

		args = self._action_args()
		args["properties"] = frappe.as_json([TEST_PROPERTY])

		result = item_price_actions.preview_item_price_schedule(**args)

		self.assertEqual(len(result), 1)
		self.assertEqual(result[0]["property"], TEST_PROPERTY)
		self.assertEqual(flt(result[0]["base_rate"]), 1000)

	def _ensure_second_property(self):
		"""Create a second property owning its own service item.

		Item Prices are keyed by item, price list and customer, so a second
		property needs a distinct service item to have its own schedule.
		"""
		self._second_item = SECOND_ITEM
		factories.ensure_item(SECOND_ITEM)
		factories.ensure_property(SECOND_PROPERTY, service_item=SECOND_ITEM)

		return SECOND_PROPERTY


	def test_replace_existing_removes_prior_generated_prices(self):
		item_price_actions.create_item_price_schedule(**self._action_args())

		args = self._action_args()
		args["replace_existing"] = 1
		args["end_date"] = "2026-06-30"
		result = item_price_actions.create_item_price_schedule(**args)

		self.assertEqual(result["created_count"], 1)
		self.assertEqual(result["skipped"], 0)
		self.assertEqual(
			getdate(result["schedule"][0]["periods"][0]["valid_upto"]), getdate("2026-06-30")
		)

		remaining = frappe.get_all(
			"Item Price",
			filters={"item_code": TEST_ITEM, "price_list": TEST_PRICE_LIST},
			pluck="name",
		)
		self.assertEqual(len(remaining), 1)
