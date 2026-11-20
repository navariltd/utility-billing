"""Tests for price list resolution on a Utility Service Request.

Covers the fallback order: the request's own price list, then the customer's
default, then the Default Price List in Utility Billing Settings. The Customer
Group is not part of it, no price list is required, and the request never
writes a price list to a customer.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from utility_billing.utility_billing.doctype.utility_service_request.utility_service_request import (
    create_customer,
)
from utility_billing.utility_billing.tests import factories
from utility_billing.utility_billing.utils.price_list import (
    apply_default_price_list,
    resolve_price_list,
)

CUSTOMER = "_Test Price List Customer"
CUSTOMER_LIST = "_Test Customer Price List"
SETTINGS_LIST = "_Test Settings Price List"
GROUP_LIST = "_Test Group Price List"
GROUP = "_Test Price List Customer Group"


class FakeDoc:
    """Stand-in exposing only the fields ``apply_default_price_list`` reads."""

    def __init__(self, price_list=None, customer=None):
        self.price_list = price_list
        self.customer = customer

    def get(self, key):
        """Mirror ``Document.get`` for the attributes this helper touches."""
        return getattr(self, key, None)


class PriceListCase(FrappeTestCase):
    def setUp(self):
        # Looked up by name, so it also works where customers are named by series
        self.customer = frappe.db.get_value("Customer", {"customer_name": CUSTOMER}) or frappe.get_doc(
            {"doctype": "Customer", "customer_name": CUSTOMER, "customer_type": "Individual"}
        ).insert(ignore_permissions=True).name
        self._ensure_price_lists()
        self.settings_before = frappe.db.get_single_value("Utility Billing Settings", "default_price_list")
        self._set_settings_price_list(SETTINGS_LIST)
        frappe.db.set_value("Customer", self.customer, "default_price_list", None)

    def tearDown(self):
        self._set_settings_price_list(self.settings_before)
        frappe.db.rollback()

    def _ensure_price_lists(self):
        for name in (CUSTOMER_LIST, SETTINGS_LIST, GROUP_LIST):
            if not frappe.db.exists("Price List", name):
                frappe.get_doc(
                    {
                        "doctype": "Price List",
                        "price_list_name": name,
                        "enabled": 1,
                        "selling": 1,
                        "currency": frappe.db.get_default("currency"),
                    }
                ).insert(ignore_permissions=True)

    def _set_settings_price_list(self, price_list):
        frappe.db.set_single_value("Utility Billing Settings", "default_price_list", price_list)
        frappe.clear_cache(doctype="Utility Billing Settings")


class TestPriceListResolution(PriceListCase):
    def test_customer_default_price_list_is_preferred_over_settings(self):
        frappe.db.set_value("Customer", self.customer, "default_price_list", CUSTOMER_LIST)

        self.assertEqual(resolve_price_list(self.customer), CUSTOMER_LIST)

    def test_settings_price_list_is_used_when_customer_has_none(self):
        self.assertEqual(resolve_price_list(self.customer), SETTINGS_LIST)

    def test_no_price_list_configured_resolves_to_nothing(self):
        self._set_settings_price_list(None)

        self.assertIsNone(resolve_price_list(self.customer))

    def test_apply_sets_the_resolved_price_list_when_empty(self):
        doc = FakeDoc(customer=self.customer)

        apply_default_price_list(doc)

        self.assertEqual(doc.price_list, SETTINGS_LIST)

    def test_apply_never_overwrites_an_explicit_price_list(self):
        doc = FakeDoc(price_list="Manual List", customer=self.customer)

        apply_default_price_list(doc)

        self.assertEqual(doc.price_list, "Manual List")

    def test_apply_uses_the_customer_default_when_available(self):
        frappe.db.set_value("Customer", self.customer, "default_price_list", CUSTOMER_LIST)

        doc = FakeDoc(customer=self.customer)
        apply_default_price_list(doc)

        self.assertEqual(doc.price_list, CUSTOMER_LIST)

    def test_the_customer_group_is_not_part_of_the_default(self):
        if not frappe.db.exists("Customer Group", GROUP):
            frappe.get_doc(
                {"doctype": "Customer Group", "customer_group_name": GROUP, "parent_customer_group": "All Customer Groups"}
            ).insert(ignore_permissions=True)
        frappe.db.set_value("Customer Group", GROUP, "default_price_list", GROUP_LIST)
        frappe.db.set_value("Customer", self.customer, "customer_group", GROUP)

        doc = FakeDoc(customer=self.customer)
        apply_default_price_list(doc)

        self.assertEqual(doc.price_list, SETTINGS_LIST)


class TestNoRequirementAndNoCustomerWrite(PriceListCase):
    """A price list is never required, and never written to a customer."""

    def request(self, price_list=None):
        request = frappe.new_doc("Utility Service Request")
        request.update(
            {
                "service_request_from": "Customer",
                "party_name": self.customer,
                "company": frappe.db.get_value("Company", {}, "name"),
                "price_list": price_list,
            }
        )
        request.append("items", {"item_code": factories.ensure_item("_Test Price List Item"), "qty": 1, "rate": 0})
        request.flags.ignore_mandatory = True
        request.flags.ignore_links = True
        return request.insert(ignore_permissions=True)

    def test_a_request_without_a_price_list_submits(self):
        self._set_settings_price_list(None)

        request = self.request()
        request.submit()

        self.assertEqual((request.docstatus, request.price_list), (1, None))

    def test_submit_never_writes_the_customer_price_list(self):
        self.request(CUSTOMER_LIST).submit()

        self.assertIsNone(frappe.db.get_value("Customer", self.customer, "default_price_list"))

    def test_a_customer_made_from_a_lead_gets_no_price_list(self):
        lead = frappe.get_doc(
            {"doctype": "Lead", "first_name": "_Test Price List Lead", "company_name": "_Test Price List Lead Co"}
        ).insert(ignore_permissions=True)
        request = frappe.new_doc("Utility Service Request")
        request.update({"service_request_from": "Lead", "party_name": lead.name, "price_list": CUSTOMER_LIST})

        customer = create_customer(request)

        self.assertIsNone(frappe.db.get_value("Customer", customer.name, "default_price_list"))
