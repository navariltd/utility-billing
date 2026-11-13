"""Tests for price list resolution on a Utility Service Request.

Rate lookups resolve the customer's default, then the Default Price List in
Utility Billing Settings, as before. A request for a Customer defaults to the
customer's price list, then its Customer Group's, and never to Settings. A
request for a Lead, Prospect or CRM Deal gets none. Every request needs one to
be submitted, and one for a Lead, Prospect or CRM Deal also to be sent for
approval. At submit the customer gets the request's price list only when it
would otherwise have none.
"""

from types import SimpleNamespace
from unittest import skipUnless
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from utility_billing.utility_billing.doctype.utility_service_request.utility_service_request import (
    create_customer,
)
from utility_billing.utility_billing.tests import factories
from utility_billing.utility_billing.utils.price_list import (
    apply_default_price_list,
    get_default_price_list,
    require_price_list,
    resolve_price_list,
)

CUSTOMER = "_Test Price List Customer"
CUSTOMER_LIST = "_Test Customer Price List"
SETTINGS_LIST = "_Test Settings Price List"
GROUP_LIST = "_Test Group Price List"
REQUEST_LIST = "_Test Request Price List"
GROUP = "_Test Price List Customer Group"
EMPTY_GROUP = "_Test Price List Empty Group"


class FakeDoc(frappe._dict):
    """Stand-in exposing only the fields the price list helpers read."""


class PriceListCase(FrappeTestCase):
    def setUp(self):
        self.customer = factories.ensure_customer(CUSTOMER)
        for name in (CUSTOMER_LIST, SETTINGS_LIST, GROUP_LIST, REQUEST_LIST):
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
        for name, price_list in ((GROUP, GROUP_LIST), (EMPTY_GROUP, None)):
            if not frappe.db.exists("Customer Group", name):
                frappe.get_doc(
                    {"doctype": "Customer Group", "customer_group_name": name, "parent_customer_group": "All Customer Groups"}
                ).insert(ignore_permissions=True)
            frappe.db.set_value("Customer Group", name, "default_price_list", price_list)
        self.settings_before = frappe.db.get_single_value("Utility Billing Settings", "default_price_list")
        self.set_settings_price_list(SETTINGS_LIST)
        frappe.db.set_value("Customer", self.customer, {"default_price_list": None, "customer_group": EMPTY_GROUP})

    def tearDown(self):
        self.set_settings_price_list(self.settings_before)
        frappe.db.rollback()

    def set_settings_price_list(self, price_list):
        frappe.db.set_single_value("Utility Billing Settings", "default_price_list", price_list)
        frappe.clear_cache(doctype="Utility Billing Settings")

    def request(self, price_list=None, party_type="Customer", party=None):
        return FakeDoc(
            price_list=price_list,
            service_request_from=party_type,
            party_name=party or self.customer,
            customer=self.customer if party_type == "Customer" else None,
        )


class TestRateLookups(PriceListCase):
    def test_customer_default_price_list_is_preferred_over_settings(self):
        frappe.db.set_value("Customer", self.customer, "default_price_list", CUSTOMER_LIST)

        self.assertEqual(resolve_price_list(self.customer), CUSTOMER_LIST)

    def test_settings_price_list_is_used_when_customer_has_none(self):
        self.assertEqual(resolve_price_list(self.customer), SETTINGS_LIST)

    def test_the_customer_group_is_never_used(self):
        frappe.db.set_value("Customer", self.customer, "customer_group", GROUP)

        self.assertEqual(resolve_price_list(self.customer), SETTINGS_LIST)

    def test_no_price_list_configured_resolves_to_nothing(self):
        self.set_settings_price_list(None)

        self.assertIsNone(resolve_price_list(self.customer))


class TestRequestDefault(PriceListCase):
    def test_the_group_fills_a_customer_request(self):
        frappe.db.set_value("Customer", self.customer, "customer_group", GROUP)
        doc = self.request()

        apply_default_price_list(doc)

        self.assertEqual((doc.price_list, get_default_price_list(self.customer)), (GROUP_LIST, GROUP_LIST))

    def test_the_customer_default_wins_over_the_group(self):
        frappe.db.set_value("Customer", self.customer, {"default_price_list": CUSTOMER_LIST, "customer_group": GROUP})
        doc = self.request()

        apply_default_price_list(doc)

        self.assertEqual(doc.price_list, CUSTOMER_LIST)

    def test_a_price_list_chosen_by_hand_is_kept(self):
        frappe.db.set_value("Customer", self.customer, "default_price_list", CUSTOMER_LIST)
        doc = self.request(price_list=REQUEST_LIST)

        apply_default_price_list(doc)

        self.assertEqual(doc.price_list, REQUEST_LIST)

    def test_settings_are_never_the_request_default(self):
        doc = self.request()

        apply_default_price_list(doc)

        self.assertIsNone(doc.price_list)

    def test_a_lead_gets_none(self):
        doc = self.request(party_type="Lead", party="_Test Price List Lead")

        apply_default_price_list(doc)

        self.assertIsNone(doc.price_list)
        self.assertIsNone(get_default_price_list("_Test Price List Lead"))


class TestRequired(PriceListCase):
    def submitting(self, doc):
        doc._action = "submit"
        return doc

    def test_submit_is_refused_for_a_lead_without_a_price_list(self):
        for party_type in ("Lead", "Prospect", "CRM Deal"):
            with self.subTest(party_type=party_type), self.assertRaises(frappe.ValidationError):
                require_price_list(self.submitting(self.request(party_type=party_type, party="_Test Party")))

    def test_submit_is_allowed_for_a_lead_with_a_price_list(self):
        require_price_list(self.submitting(self.request(REQUEST_LIST, party_type="Lead", party="_Test Party")))

    def test_submit_is_refused_for_a_customer_without_a_price_list(self):
        with self.assertRaises(frappe.ValidationError):
            require_price_list(self.submitting(self.request()))

    def test_submit_is_allowed_for_a_customer_with_a_price_list(self):
        require_price_list(self.submitting(self.request(REQUEST_LIST)))

    def test_a_draft_save_is_allowed_without_one(self):
        doc = self.request(party_type="Lead", party="_Test Party")
        doc.update({"doctype": "Utility Service Request", "docstatus": 0, "get_doc_before_save": lambda: None})

        require_price_list(doc)

    def test_the_first_approval_step_is_refused_and_a_recall_allowed(self):
        workflow = SimpleNamespace(
            workflow_state_field="workflow_state",
            states=[SimpleNamespace(state="Draft"), SimpleNamespace(state="Pending")],
            transitions=[
                SimpleNamespace(state="Draft", next_state="Pending"),
                SimpleNamespace(state="Pending", next_state="Draft"),
            ],
        )

        def moving(before, after):
            doc = self.request(party_type="Lead", party="_Test Party")
            doc.update(
                {
                    "doctype": "Utility Service Request",
                    "docstatus": 0,
                    "workflow_state": after,
                    "get_doc_before_save": lambda: frappe._dict(workflow_state=before),
                }
            )
            return doc

        with (
            patch("frappe.model.workflow.get_workflow_name", return_value="_Test Workflow"),
            patch.object(frappe, "get_cached_doc", return_value=workflow),
        ):
            with self.assertRaises(frappe.ValidationError):
                require_price_list(moving("Draft", "Pending"))
            require_price_list(moving("Pending", "Draft"))


class TestConversion(PriceListCase):
    def converted(self, party_type, party):
        doc = frappe.new_doc("Utility Service Request")
        doc.update({"service_request_from": party_type, "party_name": party, "price_list": REQUEST_LIST})
        return create_customer(doc)

    def lead(self):
        return (
            frappe.get_doc({"doctype": "Lead", "first_name": "_Test Price List Lead", "company_name": "_Test Price List Lead Co"})
            .insert(ignore_permissions=True)
            .name
        )

    def test_a_customer_made_from_a_lead_gets_the_price_list(self):
        customer = self.converted("Lead", self.lead())

        self.assertEqual(frappe.db.get_value("Customer", customer.name, "default_price_list"), REQUEST_LIST)

    def test_a_customer_made_from_a_prospect_gets_the_price_list(self):
        prospect = frappe.get_doc({"doctype": "Prospect", "company_name": "_Test Price List Prospect"}).insert(
            ignore_permissions=True
        )

        customer = self.converted("Prospect", prospect.name)

        self.assertEqual(frappe.db.get_value("Customer", customer.name, "default_price_list"), REQUEST_LIST)

    @skipUnless(frappe.db.has_column("Customer", "crm_deal"), "needs the CRM app's Customer field")
    def test_a_customer_made_from_a_crm_deal_gets_the_price_list(self):
        deal = frappe._dict(name="_Test Price List Deal", save=lambda: None)

        def create_from_deal(deal, method):
            # Stands in for the CRM app's conversion
            frappe.get_doc(
                {"doctype": "Customer", "customer_name": "_Test Price List Deal Customer", "crm_deal": deal.name}
            ).insert(ignore_permissions=True)

        real_get_doc = frappe.get_doc

        def get_doc(*args, **kwargs):
            return deal if args[:1] == ("CRM Deal",) else real_get_doc(*args, **kwargs)

        with (
            patch(
                "crm.fcrm.doctype.erpnext_crm_settings.erpnext_crm_settings.create_customer_in_erpnext",
                side_effect=create_from_deal,
            ),
            patch.object(frappe, "get_doc", side_effect=get_doc),
        ):
            customer = self.converted("CRM Deal", deal.name)

        self.assertEqual(frappe.db.get_value("Customer", customer.name, "default_price_list"), REQUEST_LIST)

    def test_an_existing_customer_is_never_changed(self):
        lead = self.lead()
        existing = self.converted("Lead", lead)
        frappe.db.set_value("Customer", existing.name, "default_price_list", None)

        again = self.converted("Lead", lead)

        self.assertEqual(again.name, existing.name)
        self.assertIsNone(frappe.db.get_value("Customer", existing.name, "default_price_list"))


class TestCustomerAtSubmit(PriceListCase):
    """A Customer request sets the customer's price list at submit only when it has none to use."""

    def setUp(self):
        super().setUp()
        self.item = factories.ensure_item("_Test Price List Item")
        self.company = frappe.db.get_value("Company", {}, "name")

    def default(self):
        return frappe.db.get_value("Customer", self.customer, "default_price_list")

    def submit(self, price_list):
        """Save and submit a request; return the customer's default after the draft save."""
        request = frappe.new_doc("Utility Service Request")
        request.update(
            {
                "service_request_from": "Customer",
                "party_name": self.customer,
                "company": self.company,
                "price_list": price_list,
            }
        )
        request.append("items", {"item_code": self.item, "qty": 1, "rate": 0})
        request.flags.ignore_mandatory = True
        request.flags.ignore_links = True
        request.insert(ignore_permissions=True)
        after_draft_save = self.default()
        request.submit()
        return after_draft_save

    def test_the_customer_is_set_when_neither_it_nor_its_group_has_one(self):
        self.assertIsNone(self.submit(REQUEST_LIST))

        self.assertEqual(self.default(), REQUEST_LIST)
        version = frappe.get_all(
            "Version", filters={"ref_doctype": "Customer", "docname": self.customer}, pluck="data", order_by="creation desc", limit=1
        )
        self.assertIn("default_price_list", version[0])

    def test_the_customer_is_untouched_when_its_group_has_one(self):
        frappe.db.set_value("Customer", self.customer, "customer_group", GROUP)

        self.submit(REQUEST_LIST)

        self.assertIsNone(self.default())

    def test_a_second_request_leaves_the_customer_unchanged(self):
        self.submit(REQUEST_LIST)
        self.submit(CUSTOMER_LIST)

        self.assertEqual(self.default(), REQUEST_LIST)

    def test_submit_is_refused_without_a_price_list(self):
        with self.assertRaises(frappe.ValidationError):
            self.submit(None)
