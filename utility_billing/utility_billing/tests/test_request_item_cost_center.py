"""Tests for defaulting the cost center of a request's item rows.

Under the Item Price approach every row of a request with a requested property
takes that property's cost center, else ERPNext's fallback for the item (its
default selling cost center, its item group's, the company default). With
several properties a row needs its own property or the property's service item;
anything else stays blank. A row that already has a cost center, a meter row and
a request without property are left alone, and nothing is filled under Auto
Repeat.
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from utility_billing.utility_billing.tests import factories
from utility_billing.utility_billing.utils.cost_center import (
	fill_request_item_cost_centers,
	resolve_primary_cost_center,
)

PROPERTY_A = "_Test RICC Property A"
PROPERTY_B = "_Test RICC Property B"
ITEM_A = "_Test RICC Item A"
ITEM_B = "_Test RICC Item B"
SHARED_ITEM = "_Test RICC Shared Item"
SECONDARY_ITEM = "_Test RICC Secondary Item"
CENTER_A = "_Test RICC Center A"
CENTER_B = "_Test RICC Center B"
CENTER_MANUAL = "_Test RICC Center Manual"
CENTER_COMPANY = "_Test RICC Center Company"


class TestRequestItemCostCenter(FrappeTestCase):
	def setUp(self):
		super().setUp()
		self.company = frappe.db.get_value("Company", {}, "name")
		self.center_a = self._ensure_cost_center(CENTER_A)
		self.center_b = self._ensure_cost_center(CENTER_B)
		self.center_manual = self._ensure_cost_center(CENTER_MANUAL)
		self.center_company = self._ensure_cost_center(CENTER_COMPANY)

		for item_code in (ITEM_A, ITEM_B, SHARED_ITEM, SECONDARY_ITEM):
			factories.ensure_item(item_code)
			frappe.db.delete("Item Default", {"parent": item_code})
			frappe.clear_document_cache("Item", item_code)

		factories.ensure_property(PROPERTY_A, service_item=ITEM_A)
		factories.ensure_property(PROPERTY_B, service_item=ITEM_B)
		self._set_property_cost_center(PROPERTY_A, self.center_a)
		self._set_property_cost_center(PROPERTY_B, self.center_b)

		company_default = frappe.db.get_value("Company", self.company, "cost_center")
		self.addCleanup(self._set_company_cost_center, company_default)
		self._set_company_cost_center(self.center_company)

	def _ensure_cost_center(self, cost_center_name):
		return factories.ensure_cost_center(cost_center_name, self.company)

	def _set_property_cost_center(self, property_name, cost_center):
		frappe.db.set_value("Utility Property", property_name, "cost_center", cost_center)

	def _set_company_cost_center(self, cost_center):
		frappe.db.set_value("Company", self.company, "cost_center", cost_center)
		frappe.clear_document_cache("Company", self.company)

	def _set_item_default(self, item_code, cost_center):
		# Inserted directly: saving the Item would also validate unrelated defaults.
		frappe.get_doc(
			{
				"doctype": "Item Default",
				"parent": item_code,
				"parenttype": "Item",
				"parentfield": "item_defaults",
				"company": self.company,
				"selling_cost_center": cost_center,
			}
		).db_insert()
		frappe.clear_document_cache("Item", item_code)

	def _request(self, properties, items):
		request = frappe.new_doc("Utility Service Request")
		request.company = self.company
		for property_name in properties:
			request.append("requested_properties", {"utility_property": property_name})
		for row in items:
			request.append("items", {"qty": 1, **row})

		return request

	def _fill(self, request, item_price=True, skip_rows=None):
		with patch(
			"utility_billing.utility_billing.utils.request_prices.is_item_price_approach",
			return_value=item_price,
		):
			fill_request_item_cost_centers(request, skip_rows=skip_rows)

	def test_primary_row_takes_its_property_cost_center(self):
		request = self._request([PROPERTY_A], [{"item_code": ITEM_A, "utility_property": PROPERTY_A}])

		self._fill(request)

		self.assertEqual(request.items[0].cost_center, self.center_a)

	def test_item_default_is_used_when_the_property_has_none(self):
		self._set_property_cost_center(PROPERTY_A, None)
		self._set_item_default(ITEM_A, self.center_b)

		self.assertEqual(resolve_primary_cost_center(PROPERTY_A, ITEM_A, self.company), self.center_b)

	def test_company_default_is_the_last_fallback(self):
		self._set_property_cost_center(PROPERTY_A, None)

		self.assertEqual(
			resolve_primary_cost_center(PROPERTY_A, ITEM_A, self.company), self.center_company
		)

	def test_a_cost_center_of_another_company_is_never_used(self):
		other_company = frappe.db.get_value("Company", {"name": ["!=", self.company]}, "name")
		if not other_company:
			self.skipTest("Needs a second company")

		resolved = resolve_primary_cost_center(PROPERTY_A, ITEM_A, other_company)

		self.assertNotEqual(resolved, self.center_a)
		if resolved:
			self.assertEqual(
				frappe.db.get_value("Cost Center", resolved, "company"), other_company
			)

	def test_a_manual_cost_center_is_kept(self):
		request = self._request(
			[PROPERTY_A],
			[{"item_code": ITEM_A, "utility_property": PROPERTY_A, "cost_center": self.center_manual}],
		)

		self._fill(request)

		self.assertEqual(request.items[0].cost_center, self.center_manual)

	def test_every_row_takes_the_property_cost_center_over_its_item_default(self):
		self._set_item_default(SECONDARY_ITEM, self.center_b)
		request = self._request(
			[PROPERTY_A],
			[{"item_code": ITEM_A, "utility_property": PROPERTY_A}, {"item_code": SECONDARY_ITEM}],
		)

		self._fill(request)

		self.assertEqual([row.cost_center for row in request.items], [self.center_a, self.center_a])

	def test_a_secondary_row_without_its_property_is_not_guessed_among_several(self):
		request = self._request(
			[PROPERTY_A, PROPERTY_B],
			[{"item_code": SECONDARY_ITEM}, {"item_code": SECONDARY_ITEM, "utility_property": PROPERTY_B}],
		)

		self._fill(request)

		self.assertFalse(request.items[0].cost_center)
		self.assertEqual(request.items[1].cost_center, self.center_b)

	def test_two_properties_resolve_every_row_or_leave_it_blank(self):
		request = self._request(
			[PROPERTY_A, PROPERTY_B],
			[
				{"item_code": ITEM_A, "utility_property": PROPERTY_A},
				{"item_code": ITEM_B},
				{"item_code": SECONDARY_ITEM},
				{"item_code": SECONDARY_ITEM, "utility_property": PROPERTY_A},
				{"item_code": SECONDARY_ITEM, "utility_property": PROPERTY_B},
			],
		)

		self._fill(request)

		self.assertEqual(
			[row.cost_center for row in request.items],
			[self.center_a, self.center_b, None, self.center_a, self.center_b],
		)

	def test_a_request_without_property_is_left_to_erpnext(self):
		request = self._request([], [{"item_code": SECONDARY_ITEM}])

		self._fill(request)

		self.assertFalse(request.items[0].cost_center)

	def test_meter_rows_and_submitted_rows_are_left_alone(self):
		request = self._request(
			[PROPERTY_A],
			[{"item_code": SECONDARY_ITEM, "meter_number": "_Test RICC Meter"}, {"item_code": SECONDARY_ITEM}],
		)
		request.items[1].name = "_Test RICC Submitted Row"

		self._fill(request, skip_rows={"_Test RICC Submitted Row"})

		self.assertFalse(request.items[0].cost_center)
		self.assertFalse(request.items[1].cost_center)

	def test_auto_repeat_fills_nothing(self):
		request = self._request([PROPERTY_A], [{"item_code": ITEM_A, "utility_property": PROPERTY_A}])

		self._fill(request, item_price=False)

		self.assertFalse(request.items[0].cost_center)

	def test_each_property_row_gets_its_own_cost_center(self):
		request = self._request(
			[PROPERTY_A, PROPERTY_B],
			[
				{"item_code": ITEM_A, "utility_property": PROPERTY_A},
				{"item_code": ITEM_B, "utility_property": PROPERTY_B},
			],
		)

		self._fill(request)

		self.assertEqual(
			[row.cost_center for row in request.items], [self.center_a, self.center_b]
		)

	def test_a_row_without_its_property_is_matched_by_item(self):
		request = self._request([PROPERTY_A], [{"item_code": ITEM_A}])

		self._fill(request)

		self.assertEqual(request.items[0].cost_center, self.center_a)

	def test_a_shared_service_item_is_resolved_by_the_row_property_or_left_blank(self):
		frappe.db.set_value("Utility Property", PROPERTY_A, "service_item", SHARED_ITEM)
		frappe.db.set_value("Utility Property", PROPERTY_B, "service_item", SHARED_ITEM)

		request = self._request(
			[PROPERTY_A, PROPERTY_B],
			[
				{"item_code": SHARED_ITEM, "utility_property": PROPERTY_B},
				{"item_code": SHARED_ITEM},
			],
		)

		self._fill(request)

		self.assertEqual(request.items[0].cost_center, self.center_b)
		self.assertFalse(request.items[1].cost_center)

	def test_a_request_without_company_is_left_alone(self):
		request = self._request([PROPERTY_A], [{"item_code": ITEM_A, "utility_property": PROPERTY_A}])
		request.company = None

		self._fill(request)

		self.assertFalse(request.items[0].cost_center)
