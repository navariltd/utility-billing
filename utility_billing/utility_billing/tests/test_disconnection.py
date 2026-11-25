"""Tests for disconnecting a customer's meters.

A submitted disconnection request lists the customer's Closed Warranty Claims
and enabled Auto Repeats. Disconnecting reopens the chosen claims, fills their
Disconnection Request and turns off the ticked Auto Repeats. The customer's
Status becomes Disconnected when none of its claims stays Closed, and only on a
site with the Status field. A claim cannot be closed while its meter is on
another customer's Closed claim.
"""

import unittest
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from utility_billing.utility_billing.tests import factories
from utility_billing.utility_billing.utils import disconnection
from utility_billing.utility_billing.utils.disconnection import (
    check_reading_customer,
    disconnect_meters,
    disconnect_options,
    meters_without_final_reading,
)

DISCONNECTION = "_Test Disconnection"
OTHER_TYPE = "_Test Other Request Type"
ITEM = "_Test Disconnection Item"
PROPERTY = "_Test Disconnection Property"
SETTINGS = "Utility Billing Settings"
HAS_STATUS = frappe.get_meta("Customer").has_field("custom_status")


class DisconnectionCase(FrappeTestCase):
    def setUp(self):
        self.company = frappe.db.get_value("Company", {}, "name")
        self.customer = self.new_customer("_Test Disconnection Customer")
        self.other_customer = self.new_customer("_Test Disconnection Other Customer")
        for name in (DISCONNECTION, OTHER_TYPE):
            if not frappe.db.exists("Issue Type", name):
                frappe.get_doc({"doctype": "Issue Type", "name": name, "__newname": name}).insert(ignore_permissions=True)
        factories.ensure_item(ITEM)
        self.setting_before = frappe.db.get_single_value(SETTINGS, "disconnection_request_type")
        self.set_disconnection_type(DISCONNECTION)
        frappe.local.message_log = []

    def tearDown(self):
        self.set_disconnection_type(self.setting_before)
        frappe.db.rollback()

    def set_disconnection_type(self, value):
        frappe.db.set_single_value(SETTINGS, "disconnection_request_type", value)
        frappe.clear_cache(doctype=SETTINGS)

    def new_customer(self, customer_name):
        return frappe.get_doc(
            {"doctype": "Customer", "customer_name": customer_name, "customer_type": "Individual"}
        ).insert(ignore_permissions=True).name

    def status(self, customer=None):
        return frappe.db.get_value("Customer", customer or self.customer, "custom_status")

    def request(self, request_type=DISCONNECTION, utility_property=None, submitted=True):
        request = frappe.new_doc("Utility Service Request")
        request.update(
            {
                "service_request_from": "Customer",
                "party_name": self.customer,
                "request_type": request_type,
                "company": self.company,
                "date": "2026-11-10",
                "utility_property": utility_property,
            }
        )
        request.flags.ignore_mandatory = True
        request.flags.ignore_links = True
        request.insert(ignore_permissions=True)
        if submitted:
            request.db_set("docstatus", 1)
        return request

    def auto_repeat(self, customer=None):
        order = frappe.get_doc(
            {
                "doctype": "Sales Order",
                "customer": customer or self.customer,
                "company": self.company,
                "transaction_date": "2026-11-01",
                "delivery_date": "2026-11-01",
                "items": [{"item_code": ITEM, "qty": 1, "rate": 100, "delivery_date": "2026-11-01"}],
            }
        ).insert(ignore_permissions=True)
        return frappe.get_doc(
            {
                "doctype": "Auto Repeat",
                "reference_doctype": "Sales Order",
                "reference_document": order.name,
                "frequency": "Monthly",
                "start_date": "2026-11-01",
            }
        ).insert(ignore_permissions=True).name

    def claim(self, serial_no, customer=None, status="Closed", utility_property=None):
        if not frappe.db.exists("Serial No", serial_no):
            frappe.get_doc(
                {"doctype": "Serial No", "name": serial_no, "serial_no": serial_no, "item_code": ITEM, "company": self.company}
            ).db_insert()
        claim = frappe.get_doc(
            {
                "doctype": "Warranty Claim",
                "customer": customer or self.customer,
                "serial_no": serial_no,
                "status": status,
                "complaint": "_Test disconnection",
                "company": self.company,
                "complaint_date": "2026-11-01",
                "utility_property": utility_property,
            }
        )
        claim.flags.ignore_links = True
        claim.flags.ignore_mandatory = True
        return claim.insert(ignore_permissions=True).name

    def submitted_reading(self, meter_number, date, customer=None):
        name = frappe.generate_hash(length=10)
        frappe.get_doc(
            {"doctype": "Meter Reading", "name": name, "customer": customer or self.customer, "date": date, "docstatus": 1}
        ).db_insert()
        frappe.get_doc(
            {
                "doctype": "Meter Reading Item",
                "name": frappe.generate_hash(length=10),
                "parent": name,
                "parenttype": "Meter Reading",
                "parentfield": "items",
                "meter_number": meter_number,
                "docstatus": 1,
            }
        ).db_insert()

    def comments(self, doctype, name):
        return frappe.get_all(
            "Comment",
            filters={"reference_doctype": doctype, "reference_name": name, "comment_type": "Comment"},
            pluck="content",
        )


class TestOptions(DisconnectionCase):
    def test_one_claim_is_preselected_with_the_auto_repeats(self):
        claim = self.claim("_TD-ONE")
        own = self.auto_repeat()
        self.auto_repeat(self.other_customer)

        options = disconnect_options(self.request().name)

        self.assertEqual([(c.name, c.selected) for c in options["claims"]], [(claim, True)])
        self.assertEqual([(r.name, r.selected, r.reference_doctype) for r in options["auto_repeats"]], [(own, True, "Sales Order")])

    def test_several_claims_are_listed_and_nothing_is_preselected(self):
        claims = [self.claim("_TD-A"), self.claim("_TD-B")]
        self.auto_repeat()

        options = disconnect_options(self.request().name)

        self.assertEqual([c.name for c in options["claims"]], claims)
        self.assertFalse(any(c.selected for c in options["claims"]))
        self.assertFalse(any(r.selected for r in options["auto_repeats"]))

    def test_the_request_property_filters_the_claims(self):
        on_property = self.claim("_TD-ON", utility_property=PROPERTY)
        self.claim("_TD-OFF")

        options = disconnect_options(self.request(utility_property=PROPERTY).name)

        self.assertEqual([(c.name, c.selected) for c in options["claims"]], [(on_property, True)])

    def test_all_claims_are_listed_when_none_is_on_the_request_property(self):
        claims = [self.claim("_TD-A"), self.claim("_TD-B")]

        options = disconnect_options(self.request(utility_property=PROPERTY).name)

        self.assertEqual([c.name for c in options["claims"]], claims)

    def test_meters_without_a_final_reading_are_flagged(self):
        self.claim("_TD-READ")
        self.claim("_TD-EARLY")
        self.claim("_TD-NONE")
        self.claim("_TD-OPEN", status="Open")
        self.submitted_reading("_TD-READ", "2026-11-10")
        self.submitted_reading("_TD-EARLY", "2026-11-09")

        options = disconnect_options(self.request().name)

        self.assertEqual(meters_without_final_reading(self.customer, "2026-11-10"), ["_TD-EARLY", "_TD-NONE"])
        self.assertEqual(sorted(c.serial_no for c in options["claims"] if c.no_final_reading), ["_TD-EARLY", "_TD-NONE"])

    def test_not_offered_without_a_closed_claim_on_another_type_or_on_a_draft(self):
        self.assertIsNone(disconnect_options(self.request().name))

        self.claim("_TD-ONE")
        self.assertIsNone(disconnect_options(self.request(OTHER_TYPE).name))
        self.assertIsNone(disconnect_options(self.request(submitted=False).name))

        self.set_disconnection_type(None)
        self.assertIsNone(disconnect_options(self.request().name))


class TestDisconnect(DisconnectionCase):
    def test_the_chosen_claims_reopen_and_the_ticked_auto_repeats_stop(self):
        chosen, kept = self.claim("_TD-A"), self.claim("_TD-B")
        ticked, unticked = self.auto_repeat(), self.auto_repeat()
        request = self.request()

        result = disconnect_meters(request.name, [chosen], [ticked])

        claim = frappe.get_doc("Warranty Claim", chosen)
        self.assertEqual((claim.status, claim.disconnection_request, claim.resolution_date), ("Open", request.name, None))
        self.assertTrue(any(request.name in c for c in self.comments("Warranty Claim", chosen)))
        self.assertEqual(frappe.db.get_value("Warranty Claim", kept, "status"), "Closed")
        self.assertEqual(frappe.db.get_value("Auto Repeat", ticked, ["disabled", "status"]), (1, "Disabled"))
        self.assertTrue(any(request.name in c for c in self.comments("Auto Repeat", ticked)))
        self.assertEqual(frappe.db.get_value("Auto Repeat", unticked, "disabled"), 0)
        self.assertIsNone(result["status"])
        if HAS_STATUS:
            self.assertEqual(self.status(), "Active")

    def test_a_disconnected_meter_is_released(self):
        claim = self.claim("_TD-A")

        disconnect_meters(self.request().name, [claim])

        self.claim("_TD-A", self.other_customer)
        self.assertEqual(frappe.db.count("Warranty Claim", {"serial_no": "_TD-A", "status": "Closed"}), 1)

    @unittest.skipUnless(HAS_STATUS, "Customer has no custom_status field on this site")
    def test_the_customer_is_disconnected_when_no_closed_claim_remains(self):
        claims = [self.claim("_TD-A"), self.claim("_TD-B")]
        request = self.request()

        result = disconnect_meters(request.name, claims)

        self.assertEqual(result["status"], "Disconnected")
        self.assertEqual(self.status(), "Disconnected")
        self.assertTrue(any(request.name in c for c in self.comments("Customer", self.customer)))
        self.assertEqual(self.status(self.other_customer), "Active")

    @unittest.skipUnless(HAS_STATUS, "Customer has no custom_status field on this site")
    def test_the_status_is_skipped_without_the_status_field(self):
        claim = self.claim("_TD-A")

        with patch.object(disconnection, "has_status_field", return_value=False):
            result = disconnect_meters(self.request().name, [claim])

        self.assertEqual(frappe.db.get_value("Warranty Claim", claim, "status"), "Open")
        self.assertIsNone(result["status"])
        self.assertEqual(self.status(), "Active")
        self.assertEqual(self.comments("Customer", self.customer), [])

    def test_claims_and_auto_repeats_of_another_customer_are_refused_before_any_change(self):
        own = self.claim("_TD-A")
        others = self.claim("_TD-B", self.other_customer)
        open_claim = self.claim("_TD-C", status="Open")
        other_repeat = self.auto_repeat(self.other_customer)
        request = self.request()

        for claims, repeats in (([own, others], []), ([own, open_claim], []), ([own], [other_repeat])):
            with self.assertRaises(frappe.ValidationError):
                disconnect_meters(request.name, claims, repeats)

        self.assertEqual(frappe.db.get_value("Warranty Claim", own, "status"), "Closed")
        self.assertEqual(frappe.db.get_value("Auto Repeat", other_repeat, "disabled"), 0)

    def test_only_a_submitted_disconnection_request_disconnects(self):
        claim = self.claim("_TD-A")

        for request in (self.request(OTHER_TYPE), self.request(submitted=False)):
            with self.assertRaises(frappe.ValidationError):
                disconnect_meters(request.name, [claim])

        self.assertEqual(frappe.db.get_value("Warranty Claim", claim, "status"), "Closed")

    def test_names_arrive_as_json_from_the_form(self):
        claim = self.claim("_TD-A")
        repeat = self.auto_repeat()

        disconnect_meters(self.request().name, frappe.as_json([claim]), frappe.as_json([repeat]))

        self.assertEqual(frappe.db.get_value("Warranty Claim", claim, "status"), "Open")
        self.assertEqual(frappe.db.get_value("Auto Repeat", repeat, "disabled"), 1)


class TestCloseCheck(DisconnectionCase):
    def test_closing_a_claim_on_a_meter_held_elsewhere_is_refused(self):
        held = self.claim("_TD-HELD", self.other_customer)

        with self.assertRaises(frappe.ValidationError) as raised:
            self.claim("_TD-HELD")

        self.assertIn(held, str(raised.exception))
        self.assertIn(self.other_customer, str(raised.exception))

        claim = frappe.get_doc("Warranty Claim", self.claim("_TD-HELD", status="Open"))
        claim.status = "Closed"
        self.assertRaises(frappe.ValidationError, claim.save)

    def test_changing_the_serial_or_customer_of_a_closed_claim_is_checked(self):
        self.claim("_TD-HELD", self.other_customer)
        claim = frappe.get_doc("Warranty Claim", self.claim("_TD-FREE"))

        claim.serial_no = "_TD-HELD"
        self.assertRaises(frappe.ValidationError, claim.save)

    def test_the_same_customer_and_unchanged_claims_are_not_refused(self):
        self.claim("_TD-OWN")
        self.claim("_TD-OWN")

        # Records breaking the rule from before are left alone while unchanged
        first = self.claim("_TD-OLD")
        frappe.db.set_value("Warranty Claim", self.claim("_TD-OLD", status="Open"), "customer", self.other_customer)
        frappe.db.set_value("Warranty Claim", {"serial_no": "_TD-OLD", "status": "Open"}, "status", "Closed")
        claim = frappe.get_doc("Warranty Claim", first)
        claim.complaint = "_Test unchanged status"
        claim.save()

        claim.status = "Open"
        claim.save()
        claim.status = "Closed"
        self.assertRaises(frappe.ValidationError, claim.save)


class TestMeterReading(DisconnectionCase):
    @unittest.skipUnless(HAS_STATUS, "Customer has no custom_status field on this site")
    def test_a_reading_for_a_disconnected_customer_is_refused(self):
        frappe.db.set_value("Customer", self.customer, "custom_status", "Disconnected")
        reading = frappe.new_doc("Meter Reading")
        reading.update({"customer": self.customer, "date": "2026-11-10", "company": self.company})

        with self.assertRaises(frappe.ValidationError) as raised:
            reading.insert(ignore_permissions=True)

        message = str(raised.exception)
        self.assertIn(self.customer, message)
        self.assertIn("taken back", message)
        self.assertIn("close the meter's Warranty Claim again", message)
        self.assertIn("back to Active", message)

    @unittest.skipUnless(HAS_STATUS, "Customer has no custom_status field on this site")
    def test_other_statuses_and_a_site_without_the_field_are_not_refused(self):
        reading = frappe.new_doc("Meter Reading")
        reading.customer = self.customer
        for status in ("Active", "Suspended"):
            frappe.db.set_value("Customer", self.customer, "custom_status", status)
            check_reading_customer(reading)

        frappe.db.set_value("Customer", self.customer, "custom_status", "Disconnected")
        with patch.object(disconnection, "has_status_field", return_value=False):
            check_reading_customer(reading)


@unittest.skipUnless(HAS_STATUS, "Customer has no custom_status field on this site")
class TestStatusByHand(DisconnectionCase):
    """Disconnected is set through Create > Disconnect Meter, not by saving the customer."""

    MESSAGE = "A customer cannot be set to Disconnected by hand"

    def set_status(self, status, customer=None):
        doc = frappe.get_doc("Customer", customer or self.customer)
        doc.custom_status = status
        doc.save(ignore_permissions=True)

    def test_setting_disconnected_by_hand_is_refused(self):
        with self.assertRaises(frappe.ValidationError) as raised:
            self.set_status("Disconnected")

        self.assertIn(self.MESSAGE, str(raised.exception))
        self.assertIn("Create > Disconnect Meter", str(raised.exception))
        self.assertEqual(self.status(), "Active")

    def test_a_new_customer_cannot_start_disconnected(self):
        customer = frappe.get_doc(
            {
                "doctype": "Customer",
                "customer_name": "_Test Disconnection New Customer",
                "customer_type": "Individual",
                "custom_status": "Disconnected",
            }
        )
        self.assertRaises(frappe.ValidationError, customer.insert, ignore_permissions=True)

    def test_other_statuses_are_allowed(self):
        self.set_status("Suspended")
        self.assertEqual(self.status(), "Suspended")

        self.set_status("Active")
        self.assertEqual(self.status(), "Active")

    def test_an_already_disconnected_customer_can_be_saved_again(self):
        frappe.db.set_value("Customer", self.customer, "custom_status", "Disconnected")
        doc = frappe.get_doc("Customer", self.customer)
        doc.customer_details = "_Test saved again"

        doc.save(ignore_permissions=True)

        self.assertEqual(self.status(), "Disconnected")
        self.set_status("Active")
        self.assertEqual(self.status(), "Active")

    def test_allowed_while_the_setting_is_blank(self):
        self.set_disconnection_type(None)

        self.set_status("Disconnected")

        self.assertEqual(self.status(), "Disconnected")

    def test_allowed_without_the_status_field(self):
        with patch.object(disconnection, "has_status_field", return_value=False):
            self.set_status("Disconnected")

        self.assertEqual(self.status(), "Disconnected")

    def test_disconnect_meters_still_sets_the_status(self):
        claim = self.claim("_TD-A")

        result = disconnect_meters(self.request().name, [claim])

        self.assertEqual(result["status"], "Disconnected")
        self.assertEqual(self.status(), "Disconnected")
        # And the customer can be saved afterwards
        doc = frappe.get_doc("Customer", self.customer)
        doc.customer_details = "_Test saved after disconnection"
        doc.save(ignore_permissions=True)
