"""Tests for the Auto Repeat copy guard and the month end end date.

Frappe keeps an Auto Repeat's next schedule date unchanged once the next one
would pass the end date, and resets it to the start date when the Auto Repeat
is saved as Completed. The guard makes each schedule date give one copy, and a
monthly contract billed on month ends keeps its last month.
"""

import datetime
import inspect
from unittest.mock import patch

import frappe
import frappe.utils.data as frappe_dates
from frappe.automation.doctype.auto_repeat import auto_repeat as frappe_auto_repeat
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate

from utility_billing.utility_billing.doctype.utility_service_request.utility_service_request import (
    _calculate_end_date,
)
from utility_billing.utility_billing.overrides.server import auto_repeat as app_auto_repeat
from utility_billing.utility_billing.overrides.server.auto_repeat import UtilityBillingAutoRepeat, copy_is_due

ITEM = "_Test Auto Repeat Guard Item"
real_now = frappe_dates.now_datetime


def on(day):
    """Run as if today were ``day``."""
    return patch.object(
        frappe_dates, "now_datetime", lambda: datetime.datetime.combine(getdate(day), real_now().time())
    )


class TestOverride(FrappeTestCase):
    """Fails when Frappe changes what the guard relies on, or the override is no longer used."""

    def test_the_override_is_registered_and_used(self):
        from frappe.model.base_document import get_controller

        path = "utility_billing.utility_billing.overrides.server.auto_repeat.UtilityBillingAutoRepeat"
        self.assertEqual(frappe.get_hooks("override_doctype_class").get("Auto Repeat", [])[-1:], [path])
        self.assertIs(get_controller("Auto Repeat"), UtilityBillingAutoRepeat)
        self.assertTrue(issubclass(UtilityBillingAutoRepeat, frappe_auto_repeat.AutoRepeat))

    def test_frappe_signatures_are_unchanged(self):
        signature = lambda name: list(inspect.signature(getattr(frappe_auto_repeat.AutoRepeat, name)).parameters)

        self.assertEqual(signature("create_documents"), ["self"])
        self.assertEqual(signature("make_new_document"), ["self", "assignee"])
        self.assertEqual(list(inspect.signature(frappe_auto_repeat.create_repeated_entries).parameters), ["data"])

    def test_the_copy_date_is_the_next_schedule_date(self):
        # The guard reads a copy's date: Frappe sets every required Date field to it
        self.assertIn("self.next_schedule_date", inspect.getsource(frappe_auto_repeat.AutoRepeat.update_doc))


class TestEndDate(FrappeTestCase):
    def end(self, contract_end, last_day):
        return str(
            _calculate_end_date(
                start_date=getdate("2026-01-01"),
                increment_date=None,
                contract_end_date=getdate(contract_end),
                frequency="Monthly",
                repeat_on_day=0,
                repeat_on_last_day=last_day,
                has_increment=False,
                increment_interval=0,
                effective_start=0,
            )
        )

    def test_a_month_end_contract_billed_on_month_ends_ends_on_it(self):
        self.assertEqual(self.end("2026-05-31", 1), "2026-05-31")
        self.assertEqual(self.end("2027-04-30", 1), "2027-04-30")
        self.assertEqual(self.end("2028-02-29", 1), "2028-02-29")

    def test_a_contract_ending_on_the_1st_keeps_the_day_before(self):
        self.assertEqual(self.end("2026-06-01", 1), "2026-05-31")

    def test_unticked_rules_keep_the_day_before(self):
        self.assertEqual(self.end("2026-05-31", 0), "2026-05-30")
        self.assertEqual(self.end("2026-06-01", 0), "2026-05-31")


class TestCopyGuard(FrappeTestCase):
    def setUp(self):
        self.company = frappe.db.get_value("Company", {}, "name")
        self.customer = frappe.get_doc(
            {"doctype": "Customer", "customer_name": "_Test Auto Repeat Guard", "customer_type": "Individual"}
        ).insert(ignore_permissions=True).name
        if not frappe.db.exists("Item", ITEM):
            frappe.get_doc(
                {
                    "doctype": "Item",
                    "item_code": ITEM,
                    "item_group": frappe.db.get_value("Item Group", {"is_group": 0}, "name"),
                    "stock_uom": "Nos",
                    "is_stock_item": 0,
                }
            ).insert(ignore_permissions=True)

    def tearDown(self):
        frappe.db.rollback()

    def auto_repeat(self, start, end, last_day=1):
        with on(start):
            order = frappe.get_doc(
                {
                    "doctype": "Sales Order",
                    "customer": self.customer,
                    "company": self.company,
                    "transaction_date": start,
                    "delivery_date": start,
                    "items": [{"item_code": ITEM, "qty": 1, "rate": 100, "delivery_date": start}],
                }
            ).insert(ignore_permissions=True)
            return frappe.get_doc(
                {
                    "doctype": "Auto Repeat",
                    "reference_doctype": "Sales Order",
                    "reference_document": order.name,
                    "frequency": "Monthly",
                    "start_date": start,
                    "end_date": end,
                    "repeat_on_last_day": last_day,
                }
            ).insert(ignore_permissions=True)

    def copies(self, auto_repeat):
        reference = frappe.db.get_value("Auto Repeat", auto_repeat.name, "reference_document")
        return [
            str(d)
            for d in frappe.get_all(
                "Sales Order",
                filters={"auto_repeat": auto_repeat.name, "name": ("!=", reference)},
                pluck="transaction_date",
                order_by="transaction_date",
            )
        ]

    def run_daily(self, auto_repeat, start, until):
        """Run the app's and Frappe's daily steps for one Auto Repeat each day."""
        day = getdate(start)
        while day <= getdate(until):
            with on(day):
                if not frappe.db.get_value("Auto Repeat", auto_repeat.name, "disabled"):
                    app_auto_repeat.create_repeated_entries([{"name": auto_repeat.name}])
                    frappe_auto_repeat.create_repeated_entries([frappe._dict(name=auto_repeat.name)])
            day = add_days(day, 1)

    def test_each_month_end_once_with_the_last_month(self):
        auto_repeat = self.auto_repeat("2026-01-01", "2026-05-31")

        self.run_daily(auto_repeat, "2026-01-01", "2026-07-05")

        self.assertEqual(self.copies(auto_repeat), ["2026-02-28", "2026-03-31", "2026-04-30", "2026-05-31"])
        self.assertEqual(frappe.db.get_value("Auto Repeat", auto_repeat.name, "status"), "Completed")

    def test_an_unticked_rule_copies_each_month_once(self):
        auto_repeat = self.auto_repeat("2026-01-01", "2026-05-31", last_day=0)

        self.run_daily(auto_repeat, "2026-01-01", "2026-07-05")

        self.assertEqual(self.copies(auto_repeat), ["2026-02-01", "2026-03-01", "2026-04-01", "2026-05-01"])

    def test_no_copy_on_or_before_the_start_or_after_the_end(self):
        auto_repeat = self.auto_repeat("2026-01-01", "2026-05-31")

        for next_date in ("2025-12-31", "2026-01-01", "2026-06-30"):
            auto_repeat.next_schedule_date = next_date
            with self.subTest(next_date=next_date):
                self.assertFalse(copy_is_due(auto_repeat))

    def test_no_second_copy_for_a_date_and_a_cancelled_one_does_not_count(self):
        auto_repeat = self.auto_repeat("2026-01-01", "2026-05-31")
        auto_repeat.next_schedule_date = getdate("2026-02-28")
        self.assertTrue(copy_is_due(auto_repeat))

        with on("2026-02-28"):
            copy = auto_repeat.make_new_document()
        self.assertFalse(copy_is_due(auto_repeat))

        copy.db_set("docstatus", 2)
        self.assertTrue(copy_is_due(auto_repeat))
