"""Each request uses its own BOM: rows, orders and the Work Order proposal.

Two requests share one item. A request's row and order point at the latest
submitted, active BOM linked to it, else the item's default BOM, and the Work
Order proposal follows the order row. Submitted orders are never changed and
Auto Repeat copies keep ERPNext's item default. Every test rolls back.
"""

import inspect

import frappe
from erpnext.selling.doctype.sales_order.sales_order import (
	get_work_order_items as erpnext_get_work_order_items,
)
from frappe.tests import UnitTestCase
from frappe.utils import add_days, today

from utility_billing.utility_billing.doctype.utility_service_request.utility_service_request import (
	bom_new_version,
)
from utility_billing.utility_billing.overrides.server.sales_order import get_work_order_items
from utility_billing.utility_billing.tests import factories

ITEM = "_Test Request BOM Item"
RAW = "_Test Request BOM Raw"
CUSTOMER = "_Test Request BOM Customer"
ERPNEXT_METHOD = "erpnext.selling.doctype.sales_order.sales_order.get_work_order_items"
APP_METHOD = "utility_billing.utility_billing.overrides.server.sales_order.get_work_order_items"


class TestRequestBoms(UnitTestCase):
	def setUp(self):
		for item_code in (ITEM, RAW):
			factories.ensure_item(item_code)
		factories.ensure_customer(CUSTOMER)
		# Sites that name customers by series store the name apart from customer_name.
		self.customer = frappe.db.get_value("Customer", {"customer_name": CUSTOMER}, "name")
		self.company = frappe.db.get_value("Company", {}, "name")
		# The item's first submitted BOM, so ERPNext makes it the default.
		self.default = self._bom()
		self.a = self._request()
		self.b = self._request()

	def tearDown(self):
		frappe.db.rollback()

	def _bom(self):
		bom = frappe.new_doc("BOM")
		bom.item = ITEM
		bom.company = self.company
		bom.quantity = 1
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

	def _version(self, request):
		copy = bom_new_version(self._default_bom(), request.name)
		copy.insert(ignore_permissions=True)
		copy.submit()
		return copy

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

	def test_new_version_leaves_the_default_alone(self):
		own = self._version(self.a)

		self.assertEqual(frappe.db.get_value("BOM", own.name, "is_default"), 0)
		self.assertEqual(self._default_bom(), self.default.name)
		self.assertEqual(frappe.db.get_value("BOM", self.default.name, "is_default"), 1)

	def test_another_requests_default_does_not_move_this_request(self):
		own = self._version(self.a)
		order = self._sales_order(self.a)

		b_bom = self._version(self.b)
		b_bom.is_default = 1
		b_bom.save()
		self.assertEqual(self._default_bom(), b_bom.name)

		self.a.reload()
		self.a.save()
		order.reload()
		order.save()
		self.assertEqual(self.a.items[0].bom_no, own.name)
		self.assertEqual(order.items[0].bom_no, own.name)
		self.assertEqual(get_work_order_items(order.name)[0]["bom"], own.name)

	def test_a_new_request_starts_from_the_default(self):
		c = self._request()
		self.assertEqual(c.items[0].bom_no, self.default.name)

	def test_a_submitted_order_never_changes(self):
		first = self._version(self.a)
		order = self._sales_order(self.a)
		order.submit()

		later = self._version(self.a)
		self.a.reload()
		self.a.save()
		order.reload()
		self.assertEqual(self.a.items[0].bom_no, later.name)
		self.assertEqual(order.items[0].bom_no, first.name)
		self.assertEqual(get_work_order_items(order.name)[0]["bom"], first.name)

	def test_an_auto_repeat_copy_keeps_todays_behaviour(self):
		"""The copy is not given the request's BOM.

		Auto Repeat clears the no_copy ``bom_no``, and ERPNext's missing item
		details then fill in the item default, as before this change.
		"""
		own = self._version(self.a)
		order = self._sales_order(self.a)
		order.submit()

		auto_repeat = frappe.new_doc("Auto Repeat")
		auto_repeat.reference_doctype = "Sales Order"
		auto_repeat.reference_document = order.name
		auto_repeat.frequency = "Monthly"
		auto_repeat.start_date = today()
		auto_repeat.insert(ignore_permissions=True)

		copy = auto_repeat.make_new_document()
		self.assertEqual(copy.auto_repeat, auto_repeat.name)
		self.assertEqual(copy.items[0].bom_no, self._default_bom())
		self.assertNotEqual(copy.items[0].bom_no, own.name)

	def test_override_still_fits_erpnext(self):
		"""Fails on an ERPNext upgrade that would silently break the override."""
		self.assertEqual(
			frappe.get_hooks("override_whitelisted_methods").get(ERPNEXT_METHOD, [])[-1], APP_METHOD
		)
		params = ["sales_order", "for_raw_material_request"]
		self.assertEqual(list(inspect.signature(erpnext_get_work_order_items).parameters), params)
		self.assertEqual(list(inspect.signature(get_work_order_items).parameters), params)

		order = self._sales_order(self.a)
		row = erpnext_get_work_order_items(order.name)[0]
		self.assertTrue({"bom", "item_code", "sales_order_item"} <= set(row))
