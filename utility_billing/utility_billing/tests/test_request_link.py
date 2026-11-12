"""Tests for the Utility Service Request link on Warranty Claims and Meter Readings.

A request picked by hand must belong to the document's customer. A reading
takes its request from its meters' Closed claims only when they all point to
one request, and its meters must be on Closed claims of its customer. Existing
records pass these checks. Needs the link columns, which a migrate adds.
"""

from unittest import skipUnless

import frappe
from frappe.tests.utils import FrappeTestCase

from utility_billing.utility_billing.utils.request_link import (
    check_meters_of_customer,
    check_request_customer,
    make_meter_reading,
    make_meter_reading_from_claims,
    meter_reading_offered,
    request_from_claims,
    warranty_claim_defaults,
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


class TestCreateWarrantyClaim(RequestLinkCase):
    """Create > Warranty Claim: shown for a submitted request with a customer and a submitted Sales Order."""

    def submitted(self, request):
        # Only the state the button reads: submitting a request runs far more than this needs
        frappe.get_doc("Utility Service Request", request).db_set("docstatus", 1)
        return request

    def order(self, request, docstatus=1):
        order = frappe.new_doc("Sales Order")
        order.update({"customer": self.customer, "company": self.company, "utility_service_request": request})
        order.name = frappe.generate_hash(length=10)
        order.docstatus = docstatus
        order.db_insert()

    def properties(self, request, header=None, rows=()):
        doc = frappe.get_doc("Utility Service Request", request)
        if header:
            doc.db_set("utility_property", header)
        for name in rows:
            row = doc.append("requested_properties", {"utility_property": name})
            row.db_insert()

    def test_not_offered_for_a_draft_request(self):
        self.order(self.request)

        self.assertIsNone(warranty_claim_defaults(self.request))

    def test_not_offered_without_a_submitted_sales_order(self):
        self.submitted(self.request)
        self.order(self.request, docstatus=0)

        self.assertIsNone(warranty_claim_defaults(self.request))

    def test_offered_with_a_submitted_sales_order(self):
        self.order(self.submitted(self.request))

        defaults = warranty_claim_defaults(self.request)

        self.assertEqual(defaults["claims"], [])
        self.assertEqual(
            defaults["values"],
            {
                "customer": self.customer,
                "utility_property": None,
                "utility_service_request": self.request,
                "complaint_date": frappe.utils.today(),
            },
        )

    def test_the_property_comes_from_the_request_or_its_one_row(self):
        names = frappe.get_all("Utility Property", pluck="name", limit=2)
        self.order(self.submitted(self.request))
        self.order(self.submitted(self.second))
        self.properties(self.request, header=names[0])
        self.properties(self.second, rows=names[:1])

        self.assertEqual(warranty_claim_defaults(self.request)["values"]["utility_property"], names[0])
        self.assertEqual(warranty_claim_defaults(self.second)["values"]["utility_property"], names[0])

    def test_no_property_with_several_property_rows(self):
        names = frappe.get_all("Utility Property", pluck="name", limit=2)
        self.order(self.submitted(self.request))
        self.properties(self.request, rows=names)

        self.assertIsNone(warranty_claim_defaults(self.request)["values"]["utility_property"])

    def test_existing_claims_are_listed_and_cancelled_ones_left_out(self):
        self.order(self.submitted(self.request))
        first = self.claim("_TRL-M1", self.request).name
        self.claim("_TRL-M2", self.request, status="Cancelled")

        self.assertEqual(warranty_claim_defaults(self.request)["claims"], [first])


class TestCreateMeterReading(RequestLinkCase):
    """Create > Meter Reading: shown on a saved, Closed claim with a customer and a serial number."""

    def test_offered_on_a_saved_closed_claim(self):
        self.assertTrue(meter_reading_offered(self.claim("_TRL-M1")))

    def test_not_offered_on_an_open_or_unsaved_claim(self):
        self.assertFalse(meter_reading_offered(self.claim("_TRL-M1", status="Open")))
        self.assertFalse(meter_reading_offered(frappe.new_doc("Warranty Claim")))

    def test_not_offered_without_a_serial_number(self):
        claim = self.claim("_TRL-M1")
        claim.db_set("serial_no", None)

        self.assertFalse(meter_reading_offered(claim))
        with self.assertRaises(frappe.ValidationError):
            make_meter_reading(claim.name)

    def test_the_reading_is_prefilled_and_not_saved(self):
        utility_property = frappe.db.get_value("Utility Property", {}, "name")
        claim = self.claim("_TRL-M1", self.request)
        claim.db_set("utility_property", utility_property)
        frappe.db.set_value("Customer", self.customer, "default_price_list", "Standard Selling")
        readings = frappe.db.count("Meter Reading")

        reading = make_meter_reading(claim.name)

        self.assertTrue(reading.is_new())
        self.assertEqual(frappe.db.count("Meter Reading"), readings)
        self.assertEqual(
            (reading.customer, reading.property, reading.utility_service_request, reading.price_list),
            (self.customer, utility_property, self.request, "Standard Selling"),
        )
        self.assertEqual([(row.item_code, row.meter_number) for row in reading.items], [(None, "_TRL-M1")])

    def test_the_price_list_falls_back_to_the_customer_group(self):
        group = frappe.db.get_value("Customer Group", {"default_price_list": ("is", "set")}, ["name", "default_price_list"])
        frappe.db.set_value("Customer", self.customer, {"default_price_list": None, "customer_group": group[0]})

        self.assertEqual(make_meter_reading(self.claim("_TRL-M1").name).price_list, group[1])

    def test_the_prefilled_meter_passes_the_meter_rule(self):
        reading = make_meter_reading(self.claim("_TRL-M1", self.request).name)

        check_meters_of_customer(reading)
        self.assertEqual(request_from_claims(reading), self.request)


class TestMeterReadingFromSeveralClaims(RequestLinkCase):
    """Warranty Claim list: Actions > Create Meter Reading."""

    def summary(self, reading):
        return {
            "customer": reading.customer,
            "price_list": reading.price_list,
            "property": reading.property,
            "utility_service_request": reading.utility_service_request,
            "rows": [(row.item_code, row.meter_number, row.warehouse) for row in reading.items],
            "new": reading.is_new(),
        }

    def test_one_row_per_meter_and_nothing_saved(self):
        names = [self.claim("_TRL-M1").name, self.claim("_TRL-M2").name, self.claim("_TRL-M1").name]
        readings = frappe.db.count("Meter Reading")

        reading = make_meter_reading_from_claims(frappe.as_json(names))

        self.assertEqual([(row.item_code, row.meter_number, row.warehouse) for row in reading.items], [(None, "_TRL-M1", None), (None, "_TRL-M2", None)])
        self.assertTrue(reading.is_new())
        self.assertEqual(frappe.db.count("Meter Reading"), readings)

    def test_one_claim_matches_the_single_claim_button(self):
        name = self.claim("_TRL-M1", self.request).name

        self.assertEqual(self.summary(make_meter_reading_from_claims([name])), self.summary(make_meter_reading(name)))

    def test_claims_not_closed_or_without_a_serial_are_refused(self):
        closed = self.claim("_TRL-M1").name
        open_claim = self.claim("_TRL-M2", status="Open").name
        no_serial = self.claim("_TRL-M3")
        no_serial.db_set("serial_no", None)

        with self.assertRaises(frappe.ValidationError) as refused:
            make_meter_reading_from_claims([closed, open_claim, no_serial.name])
        self.assertIn(open_claim, str(refused.exception))
        self.assertIn(no_serial.name, str(refused.exception))
        self.assertNotIn(closed, str(refused.exception))

    def test_claims_of_several_customers_are_refused(self):
        names = [self.claim("_TRL-M1").name, self.claim("_TRL-M2", customer=self.other).name]

        with self.assertRaises(frappe.ValidationError):
            make_meter_reading_from_claims(names)

    def test_the_request_only_when_every_claim_has_the_same(self):
        same = [self.claim("_TRL-M1", self.request).name, self.claim("_TRL-M2", self.request).name]
        mixed = [same[0], self.claim("_TRL-M3", self.second).name]
        blank = [same[0], self.claim("_TRL-M4").name]

        self.assertEqual(make_meter_reading_from_claims(same).utility_service_request, self.request)
        self.assertIsNone(make_meter_reading_from_claims(mixed).utility_service_request)
        self.assertIsNone(make_meter_reading_from_claims(blank).utility_service_request)

    def test_the_property_only_when_every_claim_has_the_same(self):
        first, second = frappe.get_all("Utility Property", pluck="name", limit=2)
        claims = [self.claim(serial) for serial in ("_TRL-M1", "_TRL-M2", "_TRL-M3")]
        for claim, value in zip(claims, (first, first, second)):
            claim.db_set("utility_property", value)

        self.assertEqual(make_meter_reading_from_claims([c.name for c in claims[:2]]).property, first)
        self.assertIsNone(make_meter_reading_from_claims([c.name for c in claims]).property)

    def test_the_price_list_is_the_customer_default(self):
        frappe.db.set_value("Customer", self.customer, "default_price_list", "Standard Selling")
        reading = make_meter_reading_from_claims([self.claim("_TRL-M1").name, self.claim("_TRL-M2").name])

        self.assertEqual(
            (reading.customer, reading.customer_name, reading.price_list),
            (self.customer, "_Test Request Link Customer", "Standard Selling"),
        )


@skipUnless(has_link_columns(), "needs the link fields, which a migrate adds")
class TestExistingRecords(FrappeTestCase):
    def test_existing_readings_and_claims_pass_the_new_checks(self):
        for name in frappe.get_all("Meter Reading", filters={"docstatus": ("<", 2)}, pluck="name"):
            doc = frappe.get_doc("Meter Reading", name)
            with self.subTest(reading=name):
                check_meters_of_customer(doc)
                check_request_customer(doc)
        for name in frappe.get_all("Warranty Claim", pluck="name"):
            with self.subTest(claim=name):
                check_request_customer(frappe.get_doc("Warranty Claim", name))
