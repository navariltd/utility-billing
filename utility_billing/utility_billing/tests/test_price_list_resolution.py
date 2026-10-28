"""Tests for price list resolution on a Utility Service Request.

Covers the fallback order: the request's own price list, then the customer's
default, then its Customer Group's, then the Default Price List in Utility
Billing Settings, then the selling price list of Selling Settings.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from utility_billing.utility_billing.tests import factories
from utility_billing.utility_billing.utils.price_list import (
    apply_default_price_list,
    resolve_price_list,
)

CUSTOMER = "_Test Price List Customer"
CUSTOMER_LIST = "_Test Customer Price List"
SETTINGS_LIST = "_Test Settings Price List"
GROUP_LIST = "_Test Customer Group Price List"
CUSTOMER_GROUP = "_Test Price List Customer Group"
SELLING_LIST = "_Test Selling Settings Price List"


class FakeDoc:
    """Stand-in exposing only the fields ``apply_default_price_list`` reads."""

    def __init__(self, price_list=None, customer=None):
        self.price_list = price_list
        self.customer = customer

    def get(self, key):
        """Mirror ``Document.get`` for the attributes this helper touches."""
        return getattr(self, key, None)


class TestPriceListResolution(FrappeTestCase):
    def setUp(self):
        self.customer = factories.ensure_customer(CUSTOMER)
        self._ensure_customer_group()
        self.original_group = frappe.db.get_value("Customer", self.customer, "customer_group")
        frappe.db.set_value("Customer", self.customer, "customer_group", CUSTOMER_GROUP)
        self.customer_group = CUSTOMER_GROUP
        self.group_price_list = frappe.db.get_value(
            "Customer Group", self.customer_group, "default_price_list"
        )
        self.selling_price_list = frappe.db.get_single_value(
            "Selling Settings", "selling_price_list"
        )
        self._ensure_price_lists()
        self._set_settings_price_list(SETTINGS_LIST)
        self._set_customer_price_list(None)
        self._set_group_price_list(None)
        self._set_selling_price_list(SELLING_LIST)

    def tearDown(self):
        self._set_customer_price_list(None)
        self._set_settings_price_list(None)
        self._set_group_price_list(self.group_price_list)
        self._set_selling_price_list(self.selling_price_list)
        frappe.db.set_value("Customer", self.customer, "customer_group", self.original_group)
        frappe.clear_document_cache("Customer", self.customer)

    def _ensure_customer_group(self):
        if not frappe.db.exists("Customer Group", CUSTOMER_GROUP):
            frappe.get_doc(
                {
                    "doctype": "Customer Group",
                    "customer_group_name": CUSTOMER_GROUP,
                    "parent_customer_group": frappe.db.get_value(
                        "Customer Group", {"is_group": 1, "lft": 1}, "name"
                    )
                    or "All Customer Groups",
                }
            ).insert(ignore_permissions=True)

    def _set_customer_price_list(self, price_list):
        frappe.db.set_value("Customer", self.customer, "default_price_list", price_list)
        frappe.clear_document_cache("Customer", self.customer)

    def _set_group_price_list(self, price_list):
        frappe.db.set_value(
            "Customer Group", self.customer_group, "default_price_list", price_list
        )
        frappe.clear_document_cache("Customer Group", self.customer_group)

    def _set_selling_price_list(self, price_list):
        frappe.db.set_single_value("Selling Settings", "selling_price_list", price_list)
        frappe.clear_cache(doctype="Selling Settings")

    def _ensure_price_lists(self):
        for name in (CUSTOMER_LIST, SETTINGS_LIST, GROUP_LIST, SELLING_LIST):
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

    def test_customer_default_price_list_is_preferred_over_settings(self):
        self._set_customer_price_list(CUSTOMER_LIST)

        self.assertEqual(resolve_price_list(self.customer), CUSTOMER_LIST)

    def test_customer_price_list_is_preferred_over_its_group(self):
        self._set_customer_price_list(CUSTOMER_LIST)
        self._set_group_price_list(GROUP_LIST)

        self.assertEqual(resolve_price_list(self.customer), CUSTOMER_LIST)

    def test_customer_group_price_list_is_used_when_customer_has_none(self):
        self._set_group_price_list(GROUP_LIST)

        self.assertEqual(resolve_price_list(self.customer), GROUP_LIST)

    def test_settings_price_list_is_used_when_customer_has_none(self):
        self.assertEqual(resolve_price_list(self.customer), SETTINGS_LIST)

    def test_selling_settings_price_list_is_the_last_fallback(self):
        self._set_settings_price_list(None)

        self.assertEqual(resolve_price_list(self.customer), SELLING_LIST)
        self.assertEqual(resolve_price_list(None), SELLING_LIST)

    def test_no_price_list_configured_resolves_to_nothing(self):
        self._set_settings_price_list(None)
        self._set_selling_price_list(None)

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
        self._set_customer_price_list(CUSTOMER_LIST)

        doc = FakeDoc(customer=self.customer)
        apply_default_price_list(doc)

        self.assertEqual(doc.price_list, CUSTOMER_LIST)
