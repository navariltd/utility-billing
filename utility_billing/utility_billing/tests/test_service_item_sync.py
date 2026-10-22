"""Tests for auto-fetching a property's service item into the items table.

``get_service_items_for_properties`` is what the form calls when the requested
properties change, so it must return one usable row per property without
duplicating work or failing on a property that has no service item.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from utility_billing.utility_billing.doctype.utility_service_request.utility_service_request import (
	get_service_items_for_properties,
)
from utility_billing.utility_billing.tests import factories

TEST_PROPERTY_A = "_Test Sync Property A"
TEST_PROPERTY_B = "_Test Sync Property B"


class TestServiceItemsForProperties(FrappeTestCase):
	"""Resolving the rent item of each requested property."""

	def setUp(self):
		super().setUp()
		self._enable_auto_creation()
		factories.ensure_property(TEST_PROPERTY_A)
		factories.ensure_property(TEST_PROPERTY_B)

	def _enable_auto_creation(self):
		settings = frappe.get_doc("Utility Billing Settings", "Utility Billing Settings")
		settings.auto_create_service_item = 1
		settings.save(ignore_permissions=True)
		frappe.clear_cache(doctype="Utility Billing Settings")

	def test_returns_one_row_per_property(self):
		details = get_service_items_for_properties(
			frappe.as_json([TEST_PROPERTY_A, TEST_PROPERTY_B])
		)

		self.assertEqual(len(details), 2)
		self.assertEqual(
			{row["utility_property"] for row in details},
			{TEST_PROPERTY_A, TEST_PROPERTY_B},
		)

	def test_each_row_carries_the_fields_the_items_table_needs(self):
		details = get_service_items_for_properties(frappe.as_json([TEST_PROPERTY_A]))
		row = details[0]

		# These map onto Utility Service Request Item columns.
		for field in ("item_code", "item_name", "uom", "rate", "qty", "utility_property"):
			self.assertIn(field, row)

		self.assertEqual(row["utility_property"], TEST_PROPERTY_A)
		self.assertEqual(row["qty"], 1)
		self.assertTrue(row["item_code"])

	def test_the_property_service_item_is_created_and_reused(self):
		first = get_service_items_for_properties(frappe.as_json([TEST_PROPERTY_A]))
		second = get_service_items_for_properties(frappe.as_json([TEST_PROPERTY_A]))

		self.assertEqual(first[0]["item_code"], second[0]["item_code"])
		self.assertEqual(
			frappe.db.count("Item", {"item_code": first[0]["item_code"]}), 1
		)

	def test_unknown_properties_are_skipped(self):
		details = get_service_items_for_properties(
			frappe.as_json([TEST_PROPERTY_A, "_No Such Property"])
		)

		self.assertEqual(len(details), 1)
		self.assertEqual(details[0]["utility_property"], TEST_PROPERTY_A)

	def test_empty_input_returns_nothing(self):
		self.assertEqual(get_service_items_for_properties(frappe.as_json([])), [])
		self.assertEqual(get_service_items_for_properties(None), [])

	def test_accepts_a_list_as_well_as_json(self):
		details = get_service_items_for_properties([TEST_PROPERTY_A])

		self.assertEqual(len(details), 1)
		self.assertEqual(details[0]["utility_property"], TEST_PROPERTY_A)

	def test_rate_comes_from_the_item_when_no_price_list_is_given(self):
		details = get_service_items_for_properties(frappe.as_json([TEST_PROPERTY_A]))
		item_standard_rate = frappe.db.get_value(
			"Item", details[0]["item_code"], "standard_rate"
		)

		self.assertEqual(details[0]["rate"], item_standard_rate)
