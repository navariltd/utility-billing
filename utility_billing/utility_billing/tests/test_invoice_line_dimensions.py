"""Tests for filling the property and cost center of primary invoice lines.

Only under the Item Price approach: a line billing a property's service item gets
that property and its cost center, unless set by hand. Under Auto Repeat invoice
lines are left exactly as they are.
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from utility_billing.utility_billing.overrides.server import sales_invoice
from utility_billing.utility_billing.tests import factories

PROPERTY_A = "_Test ILD Property A"
PROPERTY_B = "_Test ILD Property B"
ITEM_A = "_Test ILD Item A"
SHARED_ITEM = "_Test ILD Shared Item"
SECONDARY_ITEM = "_Test ILD Secondary Item"


class TestInvoiceLineDimensions(FrappeTestCase):
	def setUp(self):
		super().setUp()
		self.company = frappe.db.get_value("Company", {}, "name")
		self.center_a = factories.ensure_cost_center("_Test ILD Center A", self.company)
		self.center_b = factories.ensure_cost_center("_Test ILD Center B", self.company)
		self.center_manual = factories.ensure_cost_center("_Test ILD Center Manual", self.company)
		self.center_company = factories.ensure_cost_center("_Test ILD Center Company", self.company)

		for item_code in (ITEM_A, SHARED_ITEM, SECONDARY_ITEM):
			factories.ensure_item(item_code)

		factories.ensure_property(PROPERTY_A, service_item=ITEM_A)
		factories.ensure_property(PROPERTY_B, service_item=SHARED_ITEM)
		frappe.db.set_value("Utility Property", PROPERTY_A, "cost_center", self.center_a)
		frappe.db.set_value("Utility Property", PROPERTY_B, "cost_center", self.center_b)

		company_default = frappe.db.get_value("Company", self.company, "cost_center")
		self.addCleanup(self._set_company_cost_center, company_default)
		self._set_company_cost_center(self.center_company)

	def _set_company_cost_center(self, cost_center):
		frappe.db.set_value("Company", self.company, "cost_center", cost_center)
		frappe.clear_document_cache("Company", self.company)

	def _invoice(self, rows, **values):
		invoice = frappe.new_doc("Sales Invoice")
		invoice.company = self.company
		invoice.update(values)
		for row in rows:
			invoice.append("items", {"qty": 1, **row})

		return invoice

	def _fill(self, invoice, item_price=True):
		with patch.object(sales_invoice, "is_item_price_approach", return_value=item_price):
			sales_invoice.fill_primary_line_dimensions(invoice)

	def test_item_price_fills_a_blank_primary_line(self):
		invoice = self._invoice([{"item_code": ITEM_A}])

		self._fill(invoice)

		self.assertEqual(invoice.items[0].utility_property, PROPERTY_A)
		self.assertEqual(invoice.items[0].cost_center, self.center_a)

	def test_item_price_replaces_the_company_default_on_a_primary_line(self):
		invoice = self._invoice([{"item_code": ITEM_A, "cost_center": self.center_company}])

		self._fill(invoice)

		self.assertEqual(invoice.items[0].utility_property, PROPERTY_A)
		self.assertEqual(invoice.items[0].cost_center, self.center_a)

	def test_auto_repeat_leaves_a_primary_line_untouched(self):
		invoice = self._invoice([{"item_code": ITEM_A, "cost_center": self.center_company}])

		self._fill(invoice, item_price=False)

		self.assertFalse(invoice.items[0].utility_property)
		self.assertEqual(invoice.items[0].cost_center, self.center_company)

	def test_a_cost_center_chosen_by_hand_is_kept(self):
		invoice = self._invoice([{"item_code": ITEM_A, "cost_center": self.center_manual}])

		self._fill(invoice)

		self.assertEqual(invoice.items[0].utility_property, PROPERTY_A)
		self.assertEqual(invoice.items[0].cost_center, self.center_manual)

	def test_a_property_set_by_hand_is_kept(self):
		invoice = self._invoice([{"item_code": ITEM_A, "utility_property": PROPERTY_B}])

		self._fill(invoice)

		self.assertEqual(invoice.items[0].utility_property, PROPERTY_B)
		self.assertFalse(invoice.items[0].cost_center)

	def test_secondary_meter_and_return_lines_are_untouched(self):
		secondary = self._invoice([{"item_code": SECONDARY_ITEM}])
		meter = self._invoice([{"item_code": ITEM_A, "meter_reading": "_Test ILD Reading"}])
		returned = self._invoice([{"item_code": ITEM_A}], is_return=1)

		for invoice in (secondary, meter, returned):
			self._fill(invoice)

			self.assertFalse(invoice.items[0].utility_property)
			self.assertFalse(invoice.items[0].cost_center)

	def test_a_shared_service_item_is_not_guessed_without_a_request(self):
		frappe.db.set_value("Utility Property", PROPERTY_A, "service_item", SHARED_ITEM)
		invoice = self._invoice([{"item_code": SHARED_ITEM}])

		self._fill(invoice)

		self.assertFalse(invoice.items[0].utility_property)
		self.assertFalse(invoice.items[0].cost_center)

	def test_a_shared_service_item_is_narrowed_by_the_linked_request(self):
		frappe.db.set_value("Utility Property", PROPERTY_A, "service_item", SHARED_ITEM)
		request = frappe.new_doc("Utility Service Request")
		request.company = self.company
		request.append("requested_properties", {"utility_property": PROPERTY_B})
		request.flags.ignore_mandatory = True
		request.flags.ignore_links = True
		request.insert(ignore_permissions=True)

		invoice = self._invoice([{"item_code": SHARED_ITEM}], utility_service_request=request.name)

		self._fill(invoice)

		self.assertEqual(invoice.items[0].utility_property, PROPERTY_B)
		self.assertEqual(invoice.items[0].cost_center, self.center_b)
