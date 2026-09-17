"""Integration tests for the property rent billing service item.

Verifies that saving a property creates (or reuses) a non-stock sales item
named after the property, and that repeated calls stay idempotent.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from utility_billing.api.sales_invoice import (
	get_line_item,
	get_line_utility_property,
)
from utility_billing.utility_billing.tests import factories
from utility_billing.utility_billing.utils.service_item import (
	create_service_item_for_property,
	get_property_of_service_item,
	get_service_item_of_property,
)


class TestPropertyServiceItem(FrappeTestCase):
	"""Service item creation for utility properties."""

	def setUp(self):
		super().setUp()
		self.property_name = "_Test Service Item Property"
		frappe.db.delete("Utility Property", {"property_name": self.property_name})
		frappe.db.delete("Item", {"item_code": self.property_name})

	def tearDown(self):
		frappe.db.delete("Item", {"item_code": self.property_name})
		frappe.db.delete("Utility Property", {"property_name": self.property_name})
		super().tearDown()

	def _make_property(self):
		"""Create a billable property, exercising the automatic item creation."""
		property_doc = frappe.new_doc("Utility Property")
		property_doc.property_name = self.property_name
		property_doc.status = "Available"
		property_doc.company = frappe.db.get_value("Company", {}, "name")
		property_doc.is_group = 0
		property_doc.is_fixed_asset = 0
		property_doc.flags.ignore_mandatory = True
		property_doc.insert(ignore_permissions=True)

		return property_doc

	def _enable_auto_creation(self, enabled=True):
		settings = frappe.get_doc("Utility Billing Settings", "Utility Billing Settings")
		settings.auto_create_service_item = 1 if enabled else 0
		settings.save(ignore_permissions=True)
		frappe.clear_cache(doctype="Utility Billing Settings")

	def test_property_save_creates_and_links_service_item(self):
		self._enable_auto_creation(True)

		property_doc = self._make_property()

		self.assertEqual(property_doc.service_item, self.property_name)
		self.assertTrue(frappe.db.exists("Item", self.property_name))

		item = frappe.get_doc("Item", self.property_name)
		self.assertEqual(item.is_stock_item, 0)
		self.assertEqual(item.is_fixed_asset, 0)
		self.assertEqual(item.is_sales_item, 1)
		self.assertEqual(item.is_utility_item, 1)

	def test_service_item_creation_is_idempotent(self):
		self._enable_auto_creation(True)
		property_doc = self._make_property()

		first = create_service_item_for_property(property_doc)
		second = create_service_item_for_property(property_doc)

		self.assertEqual(first, second)
		self.assertEqual(
			frappe.db.count("Item", {"item_code": self.property_name}), 1
		)

	def test_service_item_is_reused_when_item_already_exists(self):
		self._enable_auto_creation(True)
		if not frappe.db.exists("Item", self.property_name):
			item = frappe.new_doc("Item")
			item.item_code = self.property_name
			item.item_name = self.property_name
			item.item_group = frappe.db.get_value("Item Group", {"is_group": 0}, "name")
			item.stock_uom = "Nos"
			item.is_stock_item = 0
			item.is_sales_item = 1
			item.insert(ignore_permissions=True)

		property_doc = self._make_property()

		self.assertEqual(property_doc.service_item, self.property_name)
		self.assertEqual(
			frappe.db.count("Item", {"item_code": self.property_name}), 1
		)

	def test_no_item_is_created_for_group_properties(self):
		self._enable_auto_creation(True)

		group_doc = frappe.new_doc("Utility Property")
		group_doc.property_name = f"{self.property_name} Group"
		group_doc.is_group = 1
		group_doc.flags.ignore_mandatory = True
		group_doc.insert(ignore_permissions=True)

		try:
			self.assertFalse(group_doc.service_item)
			self.assertFalse(frappe.db.exists("Item", f"{self.property_name} Group"))
		finally:
			frappe.db.delete("Utility Property", {"name": group_doc.name})

	def test_property_of_a_service_item_is_resolved(self):
		self._enable_auto_creation(True)
		self._make_property()

		self.assertEqual(get_property_of_service_item(self.property_name), self.property_name)

	def test_property_of_a_plain_item_is_none(self):
		plain_item = factories.ensure_item("_Test Plain Service Lookup Item")

		try:
			self.assertIsNone(get_property_of_service_item(plain_item))
		finally:
			frappe.db.delete("Item", {"item_code": plain_item})

	def test_service_item_of_a_property_is_resolved(self):
		self._enable_auto_creation(True)
		self._make_property()

		self.assertEqual(get_service_item_of_property(self.property_name), self.property_name)
		self.assertIsNone(get_service_item_of_property("_Test Missing Property"))

	def test_line_api_resolves_the_property_and_its_item(self):
		self._enable_auto_creation(True)
		self._make_property()

		self.assertEqual(get_line_utility_property(self.property_name), self.property_name)
		self.assertEqual(get_line_item(self.property_name), self.property_name)
