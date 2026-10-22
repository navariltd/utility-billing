"""Tests for price list resolution on a Utility Service Request.

Covers the fallback order: the request's own price list, then the customer's
default, then the Default Price List in Utility Billing Settings.
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
        self._ensure_price_lists()
        self._set_settings_price_list(SETTINGS_LIST)
        frappe.db.set_value("Customer", self.customer, "default_price_list", None)

    def tearDown(self):
        frappe.db.set_value("Customer", self.customer, "default_price_list", None)
        self._set_settings_price_list(None)

    def _ensure_price_lists(self):
        for name in (CUSTOMER_LIST, SETTINGS_LIST):
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
