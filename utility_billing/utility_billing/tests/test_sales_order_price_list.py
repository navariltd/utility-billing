"""Tests for the price list of a Sales Order created from a Utility Service Request.

The order takes the customer's default price list, else its Customer Group's,
else the Selling Settings default. The request's own price list is not used,
line rates stay as sent, and the customer is never changed.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from utility_billing.utility_billing.doctype.utility_service_request.utility_service_request import (
    create_sales_order_doc,
)
from utility_billing.utility_billing.tests import factories

CUSTOMER = "_Test Order Price List Customer"
ITEM = "_Test Order Price List Item"
REQUEST_LIST = "_Test Order Request List"
CUSTOMER_LIST = "_Test Order Customer List"
GROUP_LIST = "_Test Order Group List"
GROUP = "_Test Order Price List Group"
EMPTY_GROUP = "_Test Order Price List Empty Group"


class TestSalesOrderPriceList(FrappeTestCase):
    def setUp(self):
        self.customer = factories.ensure_customer(CUSTOMER)
        self.item = factories.ensure_item(ITEM)
        for name in (REQUEST_LIST, CUSTOMER_LIST, GROUP_LIST):
            factories.ensure_price_list(name)
        for name, price_list in ((GROUP, GROUP_LIST), (EMPTY_GROUP, None)):
            if not frappe.db.exists("Customer Group", name):
                frappe.get_doc(
                    {"doctype": "Customer Group", "customer_group_name": name, "parent_customer_group": "All Customer Groups"}
                ).insert(ignore_permissions=True)
            frappe.db.set_value("Customer Group", name, "default_price_list", price_list)
        frappe.db.set_value("Customer", self.customer, {"default_price_list": None, "customer_group": EMPTY_GROUP})
        self.company = frappe.db.get_value("Company", {}, "name")

    def tearDown(self):
        frappe.db.rollback()

    def order(self):
        """Create an order from a request whose own price list is REQUEST_LIST."""
        request = frappe.new_doc("Utility Service Request")
        request.update(
            {
                "service_request_from": "Customer",
                "party_name": self.customer,
                "company": self.company,
                "price_list": REQUEST_LIST,
            }
        )
        request.append("items", {"item_code": self.item, "qty": 1, "rate": 0})
        request.flags.ignore_mandatory = True
        request.flags.ignore_links = True
        request.insert(ignore_permissions=True)

        name = create_sales_order_doc(request.name, [{"item_code": self.item, "qty": 1, "rate": 150}])
        return frappe.get_doc("Sales Order", name)

    def test_the_customer_default_wins(self):
        frappe.db.set_value("Customer", self.customer, {"default_price_list": CUSTOMER_LIST, "customer_group": GROUP})

        order = self.order()

        self.assertEqual(order.selling_price_list, CUSTOMER_LIST)
        self.assertEqual(order.price_list_currency, frappe.db.get_value("Price List", CUSTOMER_LIST, "currency"))

    def test_the_group_is_used_when_the_customer_has_none(self):
        frappe.db.set_value("Customer", self.customer, "customer_group", GROUP)

        self.assertEqual(self.order().selling_price_list, GROUP_LIST)

    def test_selling_settings_are_the_last_fallback(self):
        self.assertEqual(
            self.order().selling_price_list,
            frappe.db.get_single_value("Selling Settings", "selling_price_list") or "Standard Selling",
        )

    def test_the_request_price_list_is_ignored(self):
        self.assertNotEqual(self.order().selling_price_list, REQUEST_LIST)

    def test_line_rates_stay_as_sent_and_the_customer_is_untouched(self):
        frappe.db.set_value("Customer", self.customer, "default_price_list", CUSTOMER_LIST)
        frappe.get_doc(
            {"doctype": "Item Price", "item_code": self.item, "price_list": CUSTOMER_LIST, "price_list_rate": 999}
        ).insert(ignore_permissions=True)
        before = frappe.db.get_value("Customer", self.customer, ["default_price_list", "customer_group", "modified"])

        order = self.order()

        self.assertEqual([(row.rate, row.amount) for row in order.items], [(150, 150)])
        self.assertEqual(frappe.db.get_value("Customer", self.customer, ["default_price_list", "customer_group", "modified"]), before)
