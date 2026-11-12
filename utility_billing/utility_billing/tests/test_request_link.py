"""Tests for the Utility Service Request link on Warranty Claims and Meter Readings.

A request picked by hand must belong to the document's customer. A reading
takes its request from its meters' Closed claims only when they all point to
one request, and its meters must be on Closed claims of its customer. Existing
records keep a blank link. Needs the link columns, which a migrate adds.
"""

from unittest import skipUnless

import frappe
from frappe.tests.utils import FrappeTestCase

from utility_billing.utility_billing.utils.request_link import (
    check_meters_of_customer,
    check_request_customer,
    request_from_claims,
)

METER_ITEM = "_Test Request Link Meter"


def has_link_columns() -> bool:
    return all(frappe.db.has_column(dt, "utility_service_request") for dt in ("Warranty Claim", "Meter Reading"))


@skipUnless(has_link_columns(), "needs the link fields, which a migrate adds")
class RequestLinkCase(FrappeTestCase):
    def setUp(self):
        self.company = frappe.db.get_value("Company", {}, "name")
        self.customer = self.make_customer("_Test Request Link Customer")
        self.other = self.make_customer("_Test Request Link Other")
        if not frappe.db.exists("Item", METER_ITEM):
            frappe.get_doc(
                {
                    "doctype": "Item",
                    "item_code": METER_ITEM,
                    "item_group": frappe.db.get_value("Item Group", {"is_group": 0}, "name"),
                    "stock_uom": "Nos",
                    "has_serial_no": 1,
                }
            ).insert(ignore_permissions=True)
        self.request = self.make_request(self.customer)
        self.second = self.make_request(self.customer)
        self.foreign = self.make_request(self.other)

    def tearDown(self):
        frappe.db.rollback()

    def make_customer(self, name):
        return frappe.get_doc({"doctype": "Customer", "customer_name": name, "customer_type": "Individual"}).insert(
            ignore_permissions=True
        ).name

    def make_request(self, customer):
        request = frappe.new_doc("Utility Service Request")
        request.update({"service_request_from": "Customer", "party_name": customer, "company": self.company})
        request.flags.ignore_mandatory = True
        request.flags.ignore_links = True
        return request.insert(ignore_permissions=True).name

    def claim(self, serial, request=None, customer=None, status="Closed"):
        if not frappe.db.exists("Serial No", serial):
            frappe.get_doc(
                {"doctype": "Serial No", "serial_no": serial, "item_code": METER_ITEM, "company": self.company}
            ).insert(ignore_permissions=True)
        return frappe.get_doc(
            {
                "doctype": "Warranty Claim",
                "customer": customer or self.customer,
                "complaint": "test",
                "serial_no": serial,
                "item_code": METER_ITEM,
                "company": self.company,
                "status": status,
                "utility_service_request": request,
            }
        ).insert(ignore_permissions=True)

    def reading(self, *meters, request=None):
        """An unsaved reading of the customer with one row per meter."""
        doc = frappe.get_doc(
            {"doctype": "Meter Reading", "customer": self.customer, "utility_service_request": request, "items": []}
        )
        for meter in meters:
            doc.append("items", {"item_code": "Water", "meter_number": meter})
        return doc


class TestWarrantyClaim(RequestLinkCase):
    def test_a_request_of_the_same_customer_is_accepted(self):
        self.assertEqual(self.claim("_TRL-M1", self.request).utility_service_request, self.request)

    def test_a_request_of_another_customer_is_refused(self):
        with self.assertRaises(frappe.ValidationError):
            self.claim("_TRL-M1", self.foreign)

    def test_a_claim_without_a_request_saves_as_before(self):
        self.assertIsNone(self.claim("_TRL-M1").utility_service_request)


class TestMeterReading(RequestLinkCase):
    def test_the_request_is_taken_when_all_claims_agree(self):
        self.claim("_TRL-M1", self.request)
        self.claim("_TRL-M2", self.request)

        self.assertEqual(request_from_claims(self.reading("_TRL-M1", "_TRL-M2")), self.request)

    def test_blank_when_the_claims_point_to_different_requests(self):
        self.claim("_TRL-M1", self.request)
        self.claim("_TRL-M2", self.second)

        self.assertIsNone(request_from_claims(self.reading("_TRL-M1", "_TRL-M2")))

    def test_blank_when_any_claim_has_no_request(self):
        self.claim("_TRL-M1", self.request)
        self.claim("_TRL-M2")

        self.assertIsNone(request_from_claims(self.reading("_TRL-M1", "_TRL-M2")))

    def test_blank_when_a_row_has_no_meter(self):
        self.claim("_TRL-M1", self.request)

        self.assertIsNone(request_from_claims(self.reading("_TRL-M1", None)))

    def test_a_request_of_the_same_customer_may_be_picked(self):
        check_request_customer(self.reading(request=self.second))

    def test_a_request_of_another_customer_is_refused(self):
        with self.assertRaises(frappe.ValidationError):
            check_request_customer(self.reading(request=self.foreign))

    def test_a_meter_of_another_customer_is_refused(self):
        self.claim("_TRL-M1", customer=self.other)

        with self.assertRaises(frappe.ValidationError):
            check_meters_of_customer(self.reading("_TRL-M1"))

    def test_a_meter_on_an_open_claim_is_refused(self):
        self.claim("_TRL-M1", status="Open")

        with self.assertRaises(frappe.ValidationError):
            check_meters_of_customer(self.reading("_TRL-M1"))

    def test_rows_without_a_meter_are_left_as_before(self):
        check_meters_of_customer(self.reading(None))


@skipUnless(has_link_columns(), "needs the link fields, which a migrate adds")
class TestExistingRecords(FrappeTestCase):
    def test_existing_readings_and_claims_pass_and_stay_blank(self):
        for name in frappe.get_all("Meter Reading", filters={"docstatus": ("<", 2)}, pluck="name"):
            doc = frappe.get_doc("Meter Reading", name)
            with self.subTest(reading=name):
                check_meters_of_customer(doc)
                check_request_customer(doc)
                self.assertIsNone(doc.utility_service_request)
        for name in frappe.get_all("Warranty Claim", pluck="name"):
            doc = frappe.get_doc("Warranty Claim", name)
            with self.subTest(claim=name):
                check_request_customer(doc)
                self.assertIsNone(doc.utility_service_request)
