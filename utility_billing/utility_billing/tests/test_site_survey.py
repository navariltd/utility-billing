"""Tests for the site survey Issue of a Utility Service Request.

The survey carries the Lead of a Lead's request and the request's property (its
own, else its one property row's). When the party becomes a customer, the
request's survey Issues without a customer get it; a customer already set is
kept, and the Issue is not saved.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from utility_billing.utility_billing.doctype.utility_service_request.utility_service_request import (
    get_site_survey_defaults,
    make_customer,
)

LEAD = "_Test Site Survey Lead"


class SiteSurveyCase(FrappeTestCase):
    def setUp(self):
        self.company = frappe.db.get_value("Company", {}, "name")
        self.properties = frappe.get_all("Utility Property", pluck="name", limit=2)
        self.lead = frappe.get_doc(
            {"doctype": "Lead", "first_name": LEAD, "company_name": f"{LEAD} Co"}
        ).insert(ignore_permissions=True).name

    def tearDown(self):
        frappe.db.rollback()

    def request(self, party_type="Lead", party=None, header_property=None, row_properties=()):
        request = frappe.new_doc("Utility Service Request")
        request.update(
            {
                "service_request_from": party_type,
                "party_name": party or self.lead,
                "company": self.company,
                "utility_property": header_property,
            }
        )
        request.flags.ignore_mandatory = True
        request.flags.ignore_links = True
        request.insert(ignore_permissions=True)
        # Only the rows the survey reads; saving them through the request runs far more
        for name in row_properties:
            request.append("requested_properties", {"utility_property": name}).db_insert()
        return request.name

    def issue(self, request, customer=None):
        return frappe.get_doc(
            {
                "doctype": "Issue",
                "subject": "_Test site survey",
                "utility_service_request": request,
                "customer": customer,
                "company": self.company,
            }
        ).insert(ignore_permissions=True)


class TestSurveyDefaults(SiteSurveyCase):
    def test_a_lead_request_fills_the_lead(self):
        self.assertEqual(get_site_survey_defaults(self.request())["lead"], self.lead)

    def test_other_parties_fill_no_lead(self):
        customer = frappe.db.get_value("Customer", {}, "name")
        self.assertIsNone(get_site_survey_defaults(self.request("Customer", customer))["lead"])
        self.assertIsNone(get_site_survey_defaults(self.request("Prospect", "_Test Prospect"))["lead"])
        self.assertIsNone(get_site_survey_defaults(self.request("CRM Deal", "_Test Deal"))["lead"])

    def test_the_property_comes_from_the_header_else_the_one_row(self):
        first, second = self.properties
        self.assertEqual(get_site_survey_defaults(self.request(header_property=first, row_properties=[second]))["utility_property"], first)
        self.assertEqual(get_site_survey_defaults(self.request(row_properties=[second, second]))["utility_property"], second)

    def test_no_property_with_several_different_rows(self):
        self.assertIsNone(get_site_survey_defaults(self.request(row_properties=self.properties))["utility_property"])

    def test_the_company_is_not_filled(self):
        self.assertNotIn("company", get_site_survey_defaults(self.request()))


class TestCustomerAfterConversion(SiteSurveyCase):
    def test_a_converted_lead_fills_blank_survey_issues_only(self):
        request = self.request()
        blank = self.issue(request)
        other_customer = frappe.db.get_value("Customer", {}, "name")
        kept = self.issue(request, other_customer)
        status, modified = frappe.db.get_value("Issue", blank.name, ["status", "modified"])

        customer = make_customer(request)

        self.assertEqual(frappe.db.get_value("Issue", blank.name, ["customer", "customer_name"]), (customer, frappe.db.get_value("Customer", customer, "customer_name")))
        self.assertEqual(frappe.db.get_value("Issue", blank.name, ["status", "modified"]), (status, modified))
        self.assertEqual(frappe.db.get_value("Issue", kept.name, "customer"), other_customer)

    def test_a_customer_that_existed_before_is_used(self):
        request = self.request()
        existing = make_customer(self.request())
        blank = self.issue(request)

        self.assertEqual(make_customer(request), existing)
        self.assertEqual(frappe.db.get_value("Issue", blank.name, "customer"), existing)
