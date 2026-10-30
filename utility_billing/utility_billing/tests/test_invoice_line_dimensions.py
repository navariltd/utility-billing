"""Tests for giving invoice lines the cost center of their Utility Service Request.

Only under the Item Price approach, and only for lines whose item is on the
linked request: such a line takes the cost center of its request row, else of
its property, unless a cost center was chosen by hand. Without a requested
property only a cost center the request's rows agree on is used. Rent lines also
get their property. Lines of other items, meter lines, return invoices, invoices
without a request and Auto Repeat sites are left to ERPNext.
"""

from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from utility_billing.utility_billing.overrides.server import sales_invoice
from utility_billing.utility_billing.tests import factories

PROPERTY_A = "_Test ILD Property A"
PROPERTY_B = "_Test ILD Property B"
ITEM_A = "_Test ILD Item A"
ITEM_B = "_Test ILD Item B"
SHARED_ITEM = "_Test ILD Shared Item"
SECONDARY_ITEM = "_Test ILD Secondary Item"
OTHER_ITEM = "_Test ILD Other Item"


class TestInvoiceLineDimensions(FrappeTestCase):
	def setUp(self):
		super().setUp()
		self.company = frappe.db.get_value("Company", {}, "name")
		self.center_a = factories.ensure_cost_center("_Test ILD Center A", self.company)
		self.center_b = factories.ensure_cost_center("_Test ILD Center B", self.company)
		self.center_manual = factories.ensure_cost_center("_Test ILD Center Manual", self.company)
		self.center_company = factories.ensure_cost_center("_Test ILD Center Company", self.company)

		for item_code in (ITEM_A, ITEM_B, SHARED_ITEM, SECONDARY_ITEM, OTHER_ITEM):
			factories.ensure_item(item_code)

		factories.ensure_property(PROPERTY_A, service_item=ITEM_A)
		factories.ensure_property(PROPERTY_B, service_item=ITEM_B)
		frappe.db.set_value("Utility Property", PROPERTY_A, "cost_center", self.center_a)
		frappe.db.set_value("Utility Property", PROPERTY_B, "cost_center", self.center_b)

		company_default = frappe.db.get_value("Company", self.company, "cost_center")
		self.addCleanup(self._set_company_cost_center, company_default)
		self._set_company_cost_center(self.center_company)

	def _set_company_cost_center(self, cost_center):
		frappe.db.set_value("Company", self.company, "cost_center", cost_center)
		frappe.clear_document_cache("Company", self.company)

	def _request(self, properties, items):
		"""Insert a draft request; its rows keep the cost centers given here."""
		request = frappe.new_doc("Utility Service Request")
		request.company = self.company
		for property_name in properties:
			request.append("requested_properties", {"utility_property": property_name})
		for row in items:
			request.append("items", {"qty": 1, **row})
		request.flags.ignore_mandatory = True
		request.flags.ignore_links = True
		with patch(
			"utility_billing.utility_billing.utils.request_prices.is_item_price_approach",
			return_value=False,
		):
			request.insert(ignore_permissions=True)

		return request

	def _invoice(self, rows, **values):
		invoice = frappe.new_doc("Sales Invoice")
		invoice.company = self.company
		invoice.update(values)
		for row in rows:
			invoice.append("items", {"qty": 1, **row})

		return invoice

	def _fill(self, invoice, item_price=True):
		with patch.object(sales_invoice, "is_item_price_approach", return_value=item_price):
			sales_invoice.fill_request_line_dimensions(invoice)

	def test_a_blank_rent_line_gets_its_property_and_cost_center(self):
		request = self._request([PROPERTY_A], [{"item_code": ITEM_A}])
		invoice = self._invoice([{"item_code": ITEM_A}], utility_service_request=request.name)

		self._fill(invoice)

		self.assertEqual(invoice.items[0].utility_property, PROPERTY_A)
		self.assertEqual(invoice.items[0].cost_center, self.center_a)

	def test_a_secondary_line_takes_the_property_over_erpnext_defaults(self):
		item_center = factories.ensure_cost_center("_Test ILD Center Item", self.company)
		frappe.get_doc(
			{
				"doctype": "Item Default",
				"parent": SECONDARY_ITEM,
				"parenttype": "Item",
				"parentfield": "item_defaults",
				"company": self.company,
				"selling_cost_center": item_center,
			}
		).db_insert()
		frappe.clear_document_cache("Item", SECONDARY_ITEM)
		request = self._request([PROPERTY_A], [{"item_code": ITEM_A}, {"item_code": SECONDARY_ITEM}])
		invoice = self._invoice(
			[{"item_code": SECONDARY_ITEM, "cost_center": item_center}, {"item_code": SECONDARY_ITEM, "cost_center": self.center_company}],
			utility_service_request=request.name,
		)

		self._fill(invoice)

		self.assertEqual([row.cost_center for row in invoice.items], [self.center_a, self.center_a])
		self.assertFalse(invoice.items[0].utility_property)

	def test_the_request_row_cost_center_is_used(self):
		request = self._request(
			[PROPERTY_A], [{"item_code": ITEM_A}, {"item_code": SECONDARY_ITEM, "cost_center": self.center_manual}]
		)
		invoice = self._invoice([{"item_code": SECONDARY_ITEM}], utility_service_request=request.name)

		self._fill(invoice)

		self.assertEqual(invoice.items[0].cost_center, self.center_manual)

	def test_a_cost_center_chosen_by_hand_on_the_invoice_is_kept(self):
		request = self._request([PROPERTY_A], [{"item_code": ITEM_A}, {"item_code": SECONDARY_ITEM}])
		invoice = self._invoice(
			[{"item_code": ITEM_A, "cost_center": self.center_manual}, {"item_code": SECONDARY_ITEM, "cost_center": self.center_manual}],
			utility_service_request=request.name,
		)

		self._fill(invoice)

		self.assertEqual([row.cost_center for row in invoice.items], [self.center_manual, self.center_manual])

	def test_a_line_of_an_item_the_request_does_not_list_is_left_to_erpnext(self):
		request = self._request([PROPERTY_A], [{"item_code": ITEM_A}])
		invoice = self._invoice(
			[{"item_code": OTHER_ITEM, "cost_center": self.center_company}], utility_service_request=request.name
		)

		self._fill(invoice)

		self.assertEqual(invoice.items[0].cost_center, self.center_company)

	def test_several_properties_use_the_line_or_row_property_and_never_guess(self):
		request = self._request(
			[PROPERTY_A, PROPERTY_B],
			[{"item_code": ITEM_A}, {"item_code": ITEM_B}, {"item_code": SECONDARY_ITEM}],
		)
		invoice = self._invoice(
			[
				{"item_code": ITEM_B},
				{"item_code": SECONDARY_ITEM},
				{"item_code": SECONDARY_ITEM, "utility_property": PROPERTY_B},
			],
			utility_service_request=request.name,
		)

		self._fill(invoice)

		self.assertEqual(invoice.items[0].cost_center, self.center_b)
		self.assertFalse(invoice.items[1].cost_center)
		self.assertEqual(invoice.items[2].cost_center, self.center_b)

	def test_meter_return_auto_repeat_and_unlinked_invoices_are_untouched(self):
		request = self._request([PROPERTY_A], [{"item_code": ITEM_A}, {"item_code": SECONDARY_ITEM}])
		cases = [
			(self._invoice([{"item_code": SECONDARY_ITEM, "meter_reading": "_Test ILD Reading"}], utility_service_request=request.name), True),
			(self._invoice([{"item_code": ITEM_A}], utility_service_request=request.name, is_return=1), True),
			(self._invoice([{"item_code": ITEM_A}], utility_service_request=request.name), False),
			(self._invoice([{"item_code": ITEM_A}]), True),
		]

		for invoice, item_price in cases:
			self._fill(invoice, item_price=item_price)

			self.assertFalse(invoice.items[0].utility_property)
			self.assertFalse(invoice.items[0].cost_center)

	def test_a_shared_service_item_is_narrowed_by_the_linked_request(self):
		frappe.db.set_value("Utility Property", PROPERTY_A, "service_item", SHARED_ITEM)
		frappe.db.set_value("Utility Property", PROPERTY_B, "service_item", SHARED_ITEM)
		request = self._request([PROPERTY_B], [{"item_code": SHARED_ITEM}])
		invoice = self._invoice([{"item_code": SHARED_ITEM}], utility_service_request=request.name)

		self._fill(invoice)

		self.assertEqual(invoice.items[0].utility_property, PROPERTY_B)
		self.assertEqual(invoice.items[0].cost_center, self.center_b)

	def test_two_properties_with_and_without_a_stamped_rent_property(self):
		request = self._request(
			[PROPERTY_A, PROPERTY_B], [{"item_code": ITEM_A, "utility_property": PROPERTY_A}, {"item_code": ITEM_B}]
		)
		invoice = self._invoice([{"item_code": ITEM_A}, {"item_code": ITEM_B}], utility_service_request=request.name)

		self._fill(invoice)

		self.assertEqual([row.utility_property for row in invoice.items], [PROPERTY_A, PROPERTY_B])
		self.assertEqual([row.cost_center for row in invoice.items], [self.center_a, self.center_b])

	def test_a_secondary_row_with_its_own_property_takes_that_property(self):
		request = self._request(
			[PROPERTY_A, PROPERTY_B],
			[{"item_code": ITEM_A}, {"item_code": ITEM_B}, {"item_code": SECONDARY_ITEM, "utility_property": PROPERTY_B}],
		)
		invoice = self._invoice([{"item_code": SECONDARY_ITEM}], utility_service_request=request.name)

		self._fill(invoice)

		self.assertEqual(invoice.items[0].cost_center, self.center_b)

	def test_a_secondary_row_without_property_among_several_is_left_to_erpnext(self):
		request = self._request(
			[PROPERTY_A, PROPERTY_B], [{"item_code": ITEM_A}, {"item_code": ITEM_B}, {"item_code": SECONDARY_ITEM}]
		)
		invoice = self._invoice(
			[{"item_code": SECONDARY_ITEM, "cost_center": self.center_company}], utility_service_request=request.name
		)

		self._fill(invoice)

		self.assertEqual(invoice.items[0].cost_center, self.center_company)

	def test_secondary_rows_of_two_properties_are_not_guessed_for_one_line(self):
		request = self._request(
			[PROPERTY_A, PROPERTY_B],
			[
				{"item_code": ITEM_A},
				{"item_code": ITEM_B},
				{"item_code": SECONDARY_ITEM, "utility_property": PROPERTY_A},
				{"item_code": SECONDARY_ITEM, "utility_property": PROPERTY_B},
			],
		)
		invoice = self._invoice(
			[{"item_code": SECONDARY_ITEM, "cost_center": self.center_company}], utility_service_request=request.name
		)

		self._fill(invoice)

		self.assertEqual(invoice.items[0].cost_center, self.center_company)

	def test_a_request_without_property_gives_the_cost_center_its_rows_agree_on(self):
		request = self._request([], [{"item_code": SECONDARY_ITEM, "cost_center": self.center_manual}])
		invoice = self._invoice(
			[{"item_code": SECONDARY_ITEM, "cost_center": self.center_company}], utility_service_request=request.name
		)

		self._fill(invoice)

		self.assertEqual(invoice.items[0].cost_center, self.center_manual)
		self.assertFalse(invoice.items[0].utility_property)

	def test_a_request_without_property_keeps_erpnext_when_rows_are_blank_or_disagree(self):
		blank = self._request([], [{"item_code": SECONDARY_ITEM}])
		disagree = self._request(
			[],
			[
				{"item_code": SECONDARY_ITEM, "cost_center": self.center_manual},
				{"item_code": SECONDARY_ITEM, "cost_center": self.center_b},
			],
		)

		for request in (blank, disagree):
			invoice = self._invoice(
				[{"item_code": SECONDARY_ITEM, "cost_center": self.center_company}], utility_service_request=request.name
			)

			self._fill(invoice)

			self.assertEqual(invoice.items[0].cost_center, self.center_company)

	def test_a_second_line_of_a_request_item_takes_the_request_cost_center(self):
		"""Accepted limit: a line of a request item added by hand, here for another
		month, cannot be told from the request's own line and is treated alike."""
		request = self._request([PROPERTY_A], [{"item_code": ITEM_A}, {"item_code": SECONDARY_ITEM}])
		invoice = self._invoice(
			[
				{"item_code": SECONDARY_ITEM, "custom_posting_date": "2031-02-10"},
				{"item_code": SECONDARY_ITEM, "custom_posting_date": "2031-03-10", "cost_center": self.center_company},
			],
			utility_service_request=request.name,
		)

		self._fill(invoice)

		self.assertEqual([row.cost_center for row in invoice.items], [self.center_a, self.center_a])

	def test_filling_twice_changes_nothing(self):
		request = self._request([PROPERTY_A], [{"item_code": ITEM_A}, {"item_code": SECONDARY_ITEM}])
		invoice = self._invoice(
			[{"item_code": ITEM_A}, {"item_code": SECONDARY_ITEM, "cost_center": self.center_company}],
			utility_service_request=request.name,
		)

		self._fill(invoice)
		first = [(row.utility_property, row.cost_center) for row in invoice.items]
		self._fill(invoice)

		self.assertEqual([(row.utility_property, row.cost_center) for row in invoice.items], first)

	def test_before_validate_fills_for_invoices_that_skip_validate(self):
		"""The daily Item Price billing inserts invoices with ``ignore_validate``."""
		invoice = self._invoice([{"item_code": ITEM_A}])
		invoice.append("taxes", {"charge_type": "Actual", "description": "x"})
		fill = MagicMock()

		with patch.object(sales_invoice, "fill_request_line_dimensions", fill):
			sales_invoice.before_validate(invoice, "before_validate")

		fill.assert_called_once_with(invoice)


class TestRequestWithoutPropertyBilling(FrappeTestCase):
	"""A submitted request with only Gas and Water rows and no property, billed by Item Price."""

	GAS = "_Test ILD Gas"
	WATER = "_Test ILD Water"
	CUSTOMER = "_Test ILD Customer"

	def setUp(self):
		super().setUp()
		self.company = frappe.db.get_value("Company", {}, "name")
		self.center_company = frappe.db.get_value("Company", self.company, "cost_center")
		factories.ensure_item(self.GAS)
		frappe.db.set_value("Item", self.GAS, "is_utility_item", 1)
		factories.ensure_item(self.WATER)
		frappe.db.set_value("Item", self.WATER, "is_utility_item", 0)
		factories.ensure_customer(self.CUSTOMER)
		self.currency = frappe.get_cached_value("Company", self.company, "default_currency")

		saved = frappe.db.get_single_value("Utility Billing Settings", "require_contract_before_sales_invoice_creation")
		frappe.db.set_single_value("Utility Billing Settings", "require_contract_before_sales_invoice_creation", 0)
		frappe.clear_cache(doctype="Utility Billing Settings")
		self.addCleanup(self._restore_contract_setting, saved)

		request = frappe.new_doc("Utility Service Request")
		request.update(
			{
				"company": self.company,
				"service_request_from": "Customer",
				"party_name": self.CUSTOMER,
				"currency": self.currency,
				"start_date": "2031-01-01",
				"end_date": "2031-12-01",
			}
		)
		request.append("items", {"item_code": self.GAS, "qty": 1, "rate": 300})
		request.append("items", {"item_code": self.WATER, "qty": 1, "rate": 100})
		request.flags.ignore_mandatory = True
		request.flags.ignore_links = True
		request.insert(ignore_permissions=True)
		request.submit()
		self.request = request

	def _restore_contract_setting(self, value):
		frappe.db.set_single_value("Utility Billing Settings", "require_contract_before_sales_invoice_creation", value)
		frappe.clear_cache(doctype="Utility Billing Settings")

	def _validate(self, gas_rate):
		invoice = frappe.new_doc("Sales Invoice")
		invoice.update(
			{"customer": self.CUSTOMER, "company": self.company, "currency": self.currency, "posting_date": "2031-02-10"}
		)
		for item_code, rate in ((self.GAS, gas_rate), (self.WATER, 100)):
			invoice.append(
				"items",
				{
					"item_code": item_code,
					"qty": 1,
					"rate": rate,
					"custom_posting_date": "2031-02-10",
					"cost_center": self.center_company,
				},
			)
		with patch.object(sales_invoice, "is_item_price_approach", return_value=True):
			sales_invoice.validate(invoice)

		return invoice

	def test_it_links_keeps_erpnext_cost_centers_and_locks_the_gas_rate(self):
		invoice = self._validate(gas_rate=300)

		self.assertEqual(invoice.utility_service_request, self.request.name)
		self.assertEqual([row.cost_center for row in invoice.items], [self.center_company, self.center_company])
		self.assertFalse(self.request.items[0].cost_center)

		with self.assertRaises(frappe.ValidationError):
			self._validate(gas_rate=450)

