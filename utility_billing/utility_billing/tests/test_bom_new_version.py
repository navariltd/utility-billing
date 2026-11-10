"""Tests for the New Version action of the request's Create > BOM dialog.

Only the submitted, active default BOM of an item on the request can be
copied, and the copy is a draft linked to the request that is not the default.
Every test rolls back.
"""

import frappe
from frappe.tests import UnitTestCase

from utility_billing.utility_billing.doctype.utility_service_request.utility_service_request import (
	bom_new_version,
)
from utility_billing.utility_billing.tests import factories

ITEM = "_Test BOM Version Item"
OTHER = "_Test BOM Version Other"
RAW = "_Test BOM Version Raw"
CUSTOMER = "_Test BOM Version Customer"


class TestBomNewVersion(UnitTestCase):
	def setUp(self):
		for item_code in (ITEM, OTHER, RAW):
			factories.ensure_item(item_code)
		factories.ensure_customer(CUSTOMER)
		self.company = frappe.db.get_value("Company", {}, "name")
		self.request = self._request()

	def tearDown(self):
		frappe.db.rollback()

	def _bom(self, item_code=ITEM, is_default=1):
		bom = frappe.new_doc("BOM")
		bom.item = item_code
		bom.company = self.company
		bom.quantity = 1
		bom.is_default = is_default
		bom.append("items", {"item_code": RAW, "qty": 1, "rate": 10})
		bom.insert(ignore_permissions=True)
		bom.submit()
		return bom

	def _request(self):
		request = frappe.new_doc("Utility Service Request")
		request.customer = CUSTOMER
		request.company = self.company
		request.append("items", {"item_code": ITEM, "qty": 1, "rate": 0})
		request.flags.ignore_mandatory = True
		request.flags.ignore_links = True
		request.insert(ignore_permissions=True)
		return request

	def test_new_version_of_the_default_is_a_linked_draft_not_default(self):
		source = self._bom()
		self.assertEqual(source.is_default, 1)

		copy = bom_new_version(source.name, self.request.name)
		copy.insert(ignore_permissions=True)

		self.assertEqual((copy.docstatus, copy.is_active, copy.is_default), (0, 1, 0))
		self.assertEqual(copy.item, ITEM)
		self.assertEqual(copy.utility_service_request, self.request.name)

	def test_a_bom_that_is_not_the_default_is_refused(self):
		self._bom()
		other = self._bom(is_default=0)

		self.assertEqual(frappe.db.get_value("BOM", other.name, "is_default"), 0)
		self.assertRaises(frappe.ValidationError, bom_new_version, other.name, self.request.name)

	def test_an_item_not_on_the_request_is_refused(self):
		other = self._bom(OTHER)
		self.assertRaises(frappe.ValidationError, bom_new_version, other.name, self.request.name)
