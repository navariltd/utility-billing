"""Tests for where a meter's previous reading starts.

With an Opening Reading on the customer's Closed claim, the previous reading is
the customer's last submitted reading of the meter since the claim's Resolution
Date, else the Opening Reading. Without one, it is what it always was. Both
billing paths, with and without a Bill Structure Assignment, are covered.
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import get_datetime

from utility_billing.utility_billing.doctype.meter_reading.meter_reading import get_previous_invoice_reading
from utility_billing.utility_billing.tests import factories
from utility_billing.utility_billing.utils import previous_reading as module
from utility_billing.utility_billing.utils.previous_reading import (
    meter_claim,
    preview_previous_reading,
    previous_reading,
)
from utility_billing.utility_billing.utils.structure_billing import previous_assigned_reading

ITEM = "_Test Previous Reading Item"
METER = "_TPR-METER"
ASSIGNMENT = "_Test Previous Reading Assignment"
PATHS = {"invoiced": None, "assigned": ASSIGNMENT}


class PreviousReadingCase(FrappeTestCase):
    def setUp(self):
        self.company = frappe.db.get_value("Company", {}, "name")
        self.customer = self.new_customer("_Test Previous Reading Customer")
        self.new_owner = self.new_customer("_Test Previous Reading New Owner")
        factories.ensure_item(ITEM)
        self.serial(METER)
        frappe.local.message_log = []

    def tearDown(self):
        frappe.db.rollback()

    def new_customer(self, customer_name):
        return frappe.get_doc(
            {"doctype": "Customer", "customer_name": customer_name, "customer_type": "Individual"}
        ).insert(ignore_permissions=True).name

    def serial(self, serial_no):
        if not frappe.db.exists("Serial No", serial_no):
            frappe.get_doc(
                {"doctype": "Serial No", "name": serial_no, "serial_no": serial_no, "item_code": ITEM, "company": self.company}
            ).db_insert()

    def claim(self, customer=None, status="Closed", opening=None, resolved=None, serial_no=METER):
        self.serial(serial_no)
        claim = frappe.get_doc(
            {
                "doctype": "Warranty Claim",
                "customer": customer or self.customer,
                "serial_no": serial_no,
                "status": status,
                "complaint": "_Test previous reading",
                "company": self.company,
                "complaint_date": "2026-01-01",
                "opening_reading_set": int(opening is not None),
                "opening_reading": opening or 0,
            }
        )
        claim.flags.ignore_links = True
        claim.flags.ignore_mandatory = True
        claim.insert(ignore_permissions=True)
        if resolved:
            claim.db_set("resolution_date", get_datetime(resolved))
        return claim.name

    def submitted(self, current, date, customer=None, creation=None):
        """A submitted Meter Reading of the meter."""
        name = frappe.generate_hash(length=10)
        reading = frappe.get_doc(
            {
                "doctype": "Meter Reading",
                "name": name,
                "customer": customer or self.customer,
                "company": self.company,
                "date": date,
                "docstatus": 1,
            }
        )
        reading.db_insert()
        if creation:
            reading.db_set("creation", get_datetime(creation), update_modified=False)
        frappe.get_doc(
            {
                "doctype": "Meter Reading Item",
                "name": frappe.generate_hash(length=10),
                "parent": name,
                "parenttype": "Meter Reading",
                "parentfield": "items",
                "item_code": ITEM,
                "meter_number": METER,
                "current_reading": current,
                "docstatus": 1,
            }
        ).db_insert()

    def invoiced(self, current, date, customer=None):
        """A submitted Sales Invoice carrying a reading of the meter."""
        name = frappe.generate_hash(length=10)
        frappe.get_doc(
            {
                "doctype": "Sales Invoice",
                "name": name,
                "customer": customer or self.customer,
                "company": self.company,
                "posting_date": date,
                "docstatus": 1,
            }
        ).db_insert()
        frappe.get_doc(
            {
                "doctype": "Sales Invoice Meter Reading",
                "name": frappe.generate_hash(length=10),
                "parent": name,
                "parenttype": "Sales Invoice",
                "parentfield": "meter_readings",
                "item_code": ITEM,
                "meter_number": METER,
                "current_reading": current,
                "docstatus": 1,
            }
        ).db_insert()

    def history(self, current, date, customer=None):
        """A reading submitted and invoiced, as both paths see it."""
        self.submitted(current, date, customer)
        self.invoiced(current, date, customer)

    def reading(self, current, date, path, customer=None):
        reading = frappe.new_doc("Meter Reading")
        reading.update(
            {
                "customer": customer or self.customer,
                "company": self.company,
                "date": date,
                "bill_structure_assignment": PATHS[path],
            }
        )
        item = reading.append("items", {"item_code": ITEM, "meter_number": METER, "current_reading": current})
        return reading, item

    def previous(self, current, date, path, customer=None):
        """Validate a row as the save does and return its previous reading and consumption."""
        reading, item = self.reading(current, date, path, customer)
        reading.validate_item_readings(item)
        return item.previous_reading, item.consumption

    def todays_previous(self, current, date, path, customer=None):
        """The lookup as it was before Opening Reading."""
        reading, item = self.reading(current, date, path, customer)
        value = get_previous_invoice_reading(item_code=ITEM, customer=reading.customer, meter_number=METER)
        if reading.bill_structure_assignment:
            value = previous_assigned_reading(reading, item, value)
        return value

    def messages(self):
        return [m for m in frappe.local.message_log if "Opening Reading" in str(m.get("message"))]


class TestPreviousReading(PreviousReadingCase):
    def test_a_customer_with_history_and_no_opening_reading_is_unchanged(self):
        self.history(80, "2026-09-01")
        self.submitted(90, "2026-10-01")  # submitted, not invoiced yet
        self.claim(resolved="2026-10-15 09:00")

        for path, expected in (("invoiced", 80), ("assigned", 90)):
            with self.subTest(path=path):
                self.assertEqual(self.previous(100, "2026-11-01", path), (expected, 100 - expected))
                self.assertEqual(self.todays_previous(100, "2026-11-01", path), expected)

    def test_a_takeover_starts_from_the_opening_reading(self):
        self.history(80, "2026-09-01")
        self.claim(status="Open")  # the old customer's claim, disconnected
        self.claim(self.new_owner, opening=80, resolved="2026-10-01 09:00")

        for path in PATHS:
            with self.subTest(path=path):
                self.assertEqual(self.previous(120, "2026-11-01", path, self.new_owner), (80, 40))
                # Without the Opening Reading the new owner was charged the whole meter
                self.assertEqual(self.todays_previous(120, "2026-11-01", path, self.new_owner), 0)

    def test_a_reset_to_zero_on_a_reopened_and_closed_claim(self):
        self.history(500, "2026-10-01")
        claim = frappe.get_doc("Warranty Claim", self.claim(resolved="2026-09-01 09:00"))
        claim.status = "Open"
        claim.save()
        self.assertIsNone(frappe.db.get_value("Warranty Claim", claim.name, "resolution_date"))

        claim.reload()
        claim.update({"status": "Closed", "opening_reading_set": 1, "opening_reading": 0})
        claim.save()
        claim.db_set("resolution_date", get_datetime("2026-11-01 09:00"))

        for path in PATHS:
            with self.subTest(path=path):
                self.assertEqual(self.previous(10, "2026-11-15", path), (0, 10))

        # Later readings of the claim's period come first
        self.submitted(10, "2026-11-15")
        for path in PATHS:
            with self.subTest(path=path, later=True):
                self.assertEqual(self.previous(25, "2026-12-15", path), (10, 15))

    def test_a_reading_on_the_closing_day_counts_only_once_saved_after_the_close(self):
        self.submitted(500, "2026-11-01", creation="2026-11-01 08:00")
        self.claim(opening=0, resolved="2026-11-01 09:00")
        self.assertEqual(self.previous(10, "2026-11-02", "invoiced"), (0, 10))

        self.submitted(4, "2026-11-01", creation="2026-11-01 10:00")
        self.assertEqual(self.previous(10, "2026-11-02", "invoiced"), (4, 6))

    def test_a_new_meter_with_no_readings_starts_at_zero(self):
        self.claim(resolved="2026-10-01 09:00")

        self.assertEqual(self.messages(), [])
        for path in PATHS:
            with self.subTest(path=path):
                self.assertEqual(self.previous(15, "2026-11-01", path), (0, 15))

    def test_an_existing_claim_with_a_blank_opening_reading_keeps_todays_lookup(self):
        self.history(500, "2026-10-01")
        self.claim(resolved="2026-11-01 09:00")  # history before its period

        for path in PATHS:
            with self.subTest(path=path):
                self.assertEqual(self.previous(510, "2026-11-15", path), (500, 10))

    def test_the_latest_closed_claim_of_the_customer_is_used(self):
        self.claim(opening=5, resolved="2026-08-01 09:00")
        newest = self.claim(opening=7, resolved="2026-10-01 09:00")

        reading, item = self.reading(20, "2026-11-01", "invoiced")
        self.assertEqual(previous_reading(reading, item), (7, meter_claim(self.customer, METER)))
        self.assertEqual(meter_claim(self.customer, METER).name, newest)

    def test_the_preview_gives_what_the_save_uses(self):
        self.history(80, "2026-09-01")
        self.claim(status="Open")
        self.claim(self.new_owner, opening=80, resolved="2026-10-01 09:00")

        preview = preview_previous_reading(
            customer=self.new_owner, item_code=ITEM, meter_number=METER, company=self.company, date="2026-11-01"
        )

        self.assertEqual(preview["previous_reading"], self.previous(120, "2026-11-01", "invoiced", self.new_owner)[0])


class TestRefusal(PreviousReadingCase):
    def test_a_lower_reading_names_the_previous_reading_and_the_claim(self):
        self.history(80, "2026-09-01")
        claim = self.claim(resolved="2026-10-01 09:00")

        for path in PATHS:
            with self.subTest(path=path):
                reading, item = self.reading(50, "2026-11-01", path)
                with self.assertRaises(frappe.ValidationError) as raised:
                    reading.validate_item_readings(item)

                message = str(raised.exception)
                self.assertIn("previous reading 80", message)
                self.assertIn(claim, message)
                self.assertIn("Opening Reading", message)


class TestOpeningReadingWarning(PreviousReadingCase):
    def test_closing_a_claim_of_a_used_meter_warns_and_still_saves(self):
        self.submitted(80, "2026-09-01")

        claim = self.claim()

        self.assertEqual(frappe.db.get_value("Warranty Claim", claim, "status"), "Closed")
        warnings = self.messages()
        self.assertEqual(len(warnings), 1)
        self.assertEqual(warnings[0].get("indicator"), "orange")
        self.assertIn(METER, warnings[0].get("message"))

    def test_no_warning_with_an_opening_reading_or_an_unused_meter(self):
        self.claim(opening=0)
        self.claim(serial_no="_TPR-UNUSED")
        self.submitted(80, "2026-09-01")
        self.claim(opening=80)

        self.assertEqual(self.messages(), [])

    def test_an_unchanged_closed_claim_is_not_warned(self):
        claim = frappe.get_doc("Warranty Claim", self.claim())
        self.submitted(80, "2026-09-01")
        claim.complaint = "_Test unchanged status"

        claim.save()

        self.assertEqual(self.messages(), [])

    def test_the_warning_can_become_a_refusal(self):
        self.submitted(80, "2026-09-01")

        with patch.object(module, "OPENING_READING_REQUIRED", True):
            self.assertRaises(frappe.ValidationError, self.claim)
