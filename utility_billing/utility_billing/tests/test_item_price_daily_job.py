"""Tests for what the daily Item Price job skips.

The job inserts its draft invoices without validation, so it applies Require
Contract itself under Item Price: no submitted Contract, none signed when
signing is required, or every row released means no draft. It also never bills
the stored lease end when that end is whole months after the start, the day
after the last billed day. With Require Contract off, and under Auto Repeat,
it behaves as on develop.

Every test runs in a savepoint rolled back afterwards.
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from utility_billing.utility_billing.tests import lease_fixtures as fx
from utility_billing.utility_billing.utils import auto_repeat

PROPERTY = "_Test Daily Job Property"
START = "2026-01-01"
END = "2027-01-01"
MID_LEASE = "2026-06-01"


class DailyJobCase(fx.SavepointMixin, FrappeTestCase):
	approach = "Item Price"

	def setUp(self):
		super().setUp()
		fx.use_approach(self.approach)
		fx.lease_property(PROPERTY)
		self.request = fx.make_request([(PROPERTY, START, END)], START, END, billing=True)
		frappe.get_doc(
			{
				"doctype": "Item Price",
				"item_code": PROPERTY,
				"price_list": fx.PRICE_LIST,
				"customer": fx.CUSTOMER,
				"uom": "Nos",
				"price_list_rate": 5000,
				"valid_from": START,
				"valid_upto": END,
			}
		).insert(ignore_permissions=True)

	def drafts_on(self, day):
		"""Run the job as if today were ``day`` and return the drafts it made for the request."""
		with patch.object(auto_repeat, "today", return_value=day):
			auto_repeat.create_item_price_sales_invoices()

		# By the job's marker: under Item Price the request is on the line, not the header
		return frappe.get_all(
			"Sales Invoice",
			filters={"remarks": ("like", f"%AUTO-BILLING:{self.request.name}:%"), "posting_date": day, "docstatus": 0},
			pluck="grand_total",
		)

	def contract(self, signed=True, submit=True):
		return fx.make_contract(self.request.name, signed=signed, submit=submit)


class TestRequireContractOn(DailyJobCase):
	"""Require Contract on, signing required: only a signed, held Contract is billed."""

	def setUp(self):
		super().setUp()
		fx.use_approach(self.approach, require_contract=1, require_signed=1)

	def test_no_contract_is_skipped(self):
		self.assertEqual(self.drafts_on(MID_LEASE), [])

	def test_a_draft_contract_is_skipped(self):
		self.contract(submit=False)

		self.assertEqual(self.drafts_on(MID_LEASE), [])

	def test_an_unsigned_contract_is_skipped(self):
		self.contract(signed=False)

		self.assertEqual(self.drafts_on(MID_LEASE), [])

	def test_a_released_contract_is_skipped(self):
		fx.release_rows(self.contract(), 0)

		self.assertEqual(self.drafts_on(MID_LEASE), [])

	def test_a_signed_held_contract_is_billed(self):
		self.contract()

		self.assertEqual(self.drafts_on(MID_LEASE), [5000])


class TestRequireContractWithoutSigning(DailyJobCase):
	def test_an_unsigned_submitted_contract_is_billed(self):
		fx.use_approach(self.approach, require_contract=1, require_signed=0)
		self.contract(signed=False)

		self.assertEqual(self.drafts_on(MID_LEASE), [5000])


class TestRequireContractOff(DailyJobCase):
	"""With Require Contract off nothing about the Contract stops a draft."""

	def test_no_contract_is_billed(self):
		self.assertEqual(self.drafts_on(MID_LEASE), [5000])

	def test_an_unsigned_contract_is_billed(self):
		self.contract(signed=False)

		self.assertEqual(self.drafts_on(MID_LEASE), [5000])

	def test_a_released_contract_is_billed(self):
		fx.release_rows(self.contract(), 0)

		self.assertEqual(self.drafts_on(MID_LEASE), [5000])


class TestLeaseEnd(DailyJobCase):
	"""The stored end of a lease of whole months is never billed."""

	def test_the_last_month_is_billed(self):
		self.assertEqual(self.drafts_on("2026-12-01"), [5000])

	def test_the_stored_end_is_skipped(self):
		self.assertEqual(self.drafts_on(END), [])

	def test_an_inclusive_end_is_still_billed(self):
		frappe.db.set_value(
			"Contract Utility Property Item", self.request.requested_properties[0].name, "end_date", "2026-12-15"
		)

		self.assertEqual(self.drafts_on("2026-12-01"), [5000])


class TestAutoRepeatUnchanged(DailyJobCase):
	"""Under Auto Repeat the job bills as on develop, whatever the settings."""

	approach = "Auto Repeat"

	def test_require_contract_does_not_stop_the_job(self):
		fx.use_approach(self.approach, require_contract=1, require_signed=1)

		self.assertEqual(self.drafts_on(MID_LEASE), [5000])

	def test_the_stored_end_is_billed_as_before(self):
		self.assertEqual(self.drafts_on(END), [5000])
