# Copyright (c) 2024, Navari and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from utility_billing.utility_billing.tests import factories

CUSTOMER = "_Test USR Customer"
PRICE_LIST = "_Test USR Price List"


class TestUtilityServiceRequest(FrappeTestCase):
	def setUp(self):
		factories.ensure_customer(CUSTOMER)
		factories.ensure_price_list(PRICE_LIST)

	def _request(self):
		request = frappe.new_doc("Utility Service Request")
		request.customer = CUSTOMER
		request.company = frappe.db.get_value("Company", {}, "name")
		request.price_list = PRICE_LIST
		request.flags.ignore_mandatory = True
		request.flags.ignore_links = True
		return request

	def test_request_can_be_saved_without_items(self):
		"""The items table is optional; items can be added later."""
		request = self._request()
		request.insert(ignore_permissions=True)

		try:
			self.assertEqual(len(request.items), 0)
		finally:
			frappe.delete_doc(
				"Utility Service Request", request.name, force=True, ignore_permissions=True
			)

