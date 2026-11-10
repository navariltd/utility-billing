"""Tests for BOMs made with New BOM from a request's Create > BOM dialog.

Such a BOM is linked to the request, never starts as the default and may be for
a non stock item such as New Connection. A BOM linked to a request must be for one of
its items. The test items are non stock. Every test rolls back.
"""

import frappe
from frappe.tests import UnitTestCase
from frappe.utils import add_days, today

from utility_billing.utility_billing.overrides.server.sales_order import get_work_order_items
from utility_billing.utility_billing.tests import factories

ITEM = "_Test BOM Link Item"
OTHER = "_Test BOM Link Other"
FIRST = "_Test BOM Link First"
RAW = "_Test BOM Link Raw"
CUSTOMER = "_Test BOM Link Customer"


class TestBomRequestLink(UnitTestCase):
	def setUp(self):
		for item_code in (ITEM, OTHER, RAW):
			factories.ensure_item(item_code)
		factories.ensure_customer(CUSTOMER)
		# Sites that name customers by series store the name apart from customer_name.
		self.customer = frappe.db.get_value("Customer", {"customer_name": CUSTOMER}, "name")
		self.company = frappe.db.get_value("Company", {}, "name")
		# The item's first submitted BOM, so ERPNext makes it the default.
		self.default = self._bom()
		self.request = self._request()

	def tearDown(self):
		frappe.db.rollback()

	def _bom(self, item_code=ITEM, request=None, is_default=1):
		bom = frappe.new_doc("BOM")
		bom.item = item_code
		bom.company = self.company
		bom.quantity = 1
		bom.is_default = is_default
		bom.utility_service_request = request.name if request else None
		bom.append("items", {"item_code": RAW, "qty": 1, "rate": 10})
		bom.insert(ignore_permissions=True)
		bom.submit()
		return bom

	def _request(self):
		request = frappe.new_doc("Utility Service Request")
		request.customer = self.customer
		request.company = self.company
		request.append("items", {"item_code": ITEM, "qty": 1, "rate": 0})
		request.flags.ignore_mandatory = True
		request.flags.ignore_links = True
		request.insert(ignore_permissions=True)
		return request

	def _sales_order(self, request):
		so = frappe.new_doc("Sales Order")
		so.customer = self.customer
		so.company = self.company
		so.transaction_date = today()
		so.delivery_date = add_days(today(), 7)
		so.utility_service_request = request.name
		so.append("items", {"item_code": ITEM, "qty": 1, "rate": 100})
		so.insert(ignore_permissions=True)
		return so

	def _default_bom(self):
		return frappe.db.get_value("Item", ITEM, "default_bom")

	def test_a_service_item_bom_made_for_the_request_is_used(self):
		"""The New BOM path: linked, not default, for a non stock item on the request."""
		own = self._bom(request=self.request, is_default=0)
		self.assertEqual(self._default_bom(), self.default.name)

		self.request.reload()
		self.request.save()
		order = self._sales_order(self.request)
		self.assertEqual(self.request.items[0].bom_no, own.name)
		self.assertEqual(order.items[0].bom_no, own.name)
		self.assertEqual(get_work_order_items(order.name)[0]["bom"], own.name)

	def test_a_bom_for_an_item_not_on_the_request_is_refused(self):
		self.assertRaises(frappe.ValidationError, self._bom, item_code=OTHER, request=self.request)

	def test_a_bom_without_a_request_is_not_checked(self):
		self.assertTrue(self._bom(item_code=OTHER).name)

	def test_a_request_bom_never_starts_default(self):
		own = self._bom(request=self.request, is_default=1)
		self.assertEqual(own.is_default, 0)
		self.assertEqual(self._default_bom(), self.default.name)

	def test_the_first_bom_of_an_item_still_becomes_default(self):
		factories.ensure_item(FIRST)
		self.request.append("items", {"item_code": FIRST, "qty": 1, "rate": 0})
		self.request.save()
		first = self._bom(item_code=FIRST, request=self.request, is_default=1)

		first.reload()
		self.assertEqual(first.is_default, 1)
		self.assertEqual(frappe.db.get_value("Item", FIRST, "default_bom"), first.name)

	def test_a_deliberate_tick_after_insert_makes_it_default(self):
		bom = frappe.new_doc("BOM")
		bom.update({"item": ITEM, "company": self.company, "quantity": 1})
		bom.utility_service_request = self.request.name
		bom.append("items", {"item_code": RAW, "qty": 1, "rate": 10})
		bom.insert(ignore_permissions=True)
		bom.is_default = 1
		bom.save()
		bom.submit()
		self.assertEqual(self._default_bom(), bom.name)
