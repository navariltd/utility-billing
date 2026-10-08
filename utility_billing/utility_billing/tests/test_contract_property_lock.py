"""Tests for locking a Contract's properties to its Utility Service Request.

The checks take the Contract and its saved version as plain dicts, so these
tests save nothing.
"""

from datetime import date

import frappe
from frappe.tests import UnitTestCase

from utility_billing.utility_billing.overrides.server import contract as lock


def row(name="ROW-1", **values):
	return frappe._dict(
		{
			"name": name,
			"idx": 1,
			"utility_property": "P1",
			"item_code": "P1",
			"start_date": date(2026, 10, 1),
			"end_date": date(2027, 10, 1),
			"contract_length_months": 12.0,
			"adjustment_rule": "RULE-1",
			"insurance": None,
			"is_active": 1,
			**values,
		}
	)


def contract(rows, docstatus=1, utility_service_request="USR-1", from_service_request=False, **values):
	return frappe._dict(
		{
			"docstatus": docstatus,
			"utility_service_request": utility_service_request,
			"start_date": date(2026, 10, 1),
			"end_date": date(2027, 10, 1),
			"properties": rows,
			"flags": frappe._dict(from_service_request=from_service_request),
			**values,
		}
	)


class TestNewContract(UnitTestCase):
	"""Where a new Contract's properties may come from."""

	def test_contract_from_the_service_request_is_allowed(self):
		lock.check_new_contract(contract([row()], docstatus=0, from_service_request=True))

	def test_properties_added_by_hand_are_blocked(self):
		with self.assertRaises(frappe.ValidationError):
			lock.check_new_contract(contract([row()], docstatus=0))

	def test_request_link_added_by_hand_is_blocked(self):
		with self.assertRaises(frappe.ValidationError):
			lock.check_new_contract(contract([], docstatus=0))

	def test_contract_without_properties_or_request_is_allowed(self):
		lock.check_new_contract(contract([], docstatus=0, utility_service_request=None))

	def test_amending_a_contract_with_properties_is_blocked(self):
		with self.assertRaises(frappe.ValidationError):
			lock.check_new_contract(
				contract([row()], docstatus=0, from_service_request=True, amended_from="CON-1")
			)


class TestRowsUnchanged(UnitTestCase):
	"""What may change on a Contract once it is saved."""

	def test_unchanged_rows_are_allowed_whatever_the_value_format(self):
		form_row = row(start_date="2026-10-01", end_date="2027-10-01", contract_length_months="12", insurance="")

		lock.check_rows_unchanged(contract([form_row]), contract([row()]))

	def test_every_copied_field_is_locked(self):
		changes = {
			"utility_property": "P2",
			"item_code": "P2",
			"start_date": date(2026, 11, 1),
			"end_date": date(2027, 9, 1),
			"contract_length_months": 11.0,
			"adjustment_rule": "RULE-2",
			"insurance": "INS-1",
		}
		self.assertEqual(set(changes), set(lock.LOCKED_ROW_FIELDS))

		for fieldname, value in changes.items():
			with self.subTest(fieldname=fieldname), self.assertRaises(frappe.ValidationError):
				lock.check_rows_unchanged(contract([row(**{fieldname: value})]), contract([row()]))

	def test_locked_fields_are_checked_on_a_draft_too(self):
		with self.assertRaises(frappe.ValidationError):
			lock.check_rows_unchanged(
				contract([row(end_date=date(2028, 1, 1))], docstatus=0), contract([row()], docstatus=0)
			)

	def test_adding_a_row_is_blocked(self):
		with self.assertRaises(frappe.ValidationError):
			lock.check_rows_unchanged(contract([row(), row(name="ROW-2")]), contract([row()]))

	def test_removing_a_row_is_blocked(self):
		with self.assertRaises(frappe.ValidationError):
			lock.check_rows_unchanged(contract([]), contract([row()]))

	def test_replacing_a_row_is_blocked(self):
		with self.assertRaises(frappe.ValidationError):
			lock.check_rows_unchanged(contract([row(name="ROW-2")]), contract([row()]))

	def test_changing_the_request_link_is_blocked(self):
		with self.assertRaises(frappe.ValidationError):
			lock.check_rows_unchanged(
				contract([row()], docstatus=0, utility_service_request="USR-2"),
				contract([row()], docstatus=0),
			)

	def test_deactivating_a_row_after_submit_is_allowed(self):
		lock.check_rows_unchanged(contract([row(is_active=0)]), contract([row()]))

	def test_reactivating_a_row_after_submit_is_blocked(self):
		with self.assertRaises(frappe.ValidationError):
			lock.check_rows_unchanged(contract([row(is_active=1)]), contract([row(is_active=0)]))

	def test_reactivating_a_row_on_a_draft_is_allowed(self):
		lock.check_rows_unchanged(
			contract([row(is_active=1)], docstatus=0), contract([row(is_active=0)], docstatus=0)
		)

	def test_signing_with_unchanged_rows_is_allowed(self):
		lock.check_rows_unchanged(contract([row()], is_signed=1), contract([row()], is_signed=0))


class TestHeaderDates(UnitTestCase):
	"""The start and end dates of a Contract linked to a request."""

	def test_unchanged_dates_are_allowed_whatever_the_value_format(self):
		lock.check_rows_unchanged(
			contract([row()], start_date="2026-10-01", end_date="2027-10-01"), contract([row()])
		)

	def test_dates_of_a_submitted_contract_are_locked(self):
		for fieldname in lock.LOCKED_HEADER_FIELDS:
			with self.subTest(fieldname=fieldname), self.assertRaises(frappe.ValidationError):
				lock.check_rows_unchanged(contract([row()], **{fieldname: date(2028, 10, 1)}), contract([row()]))

	def test_dates_of_a_draft_are_locked(self):
		for fieldname in lock.LOCKED_HEADER_FIELDS:
			with self.subTest(fieldname=fieldname), self.assertRaises(frappe.ValidationError):
				lock.check_rows_unchanged(
					contract([row()], docstatus=0, **{fieldname: date(2028, 10, 1)}),
					contract([row()], docstatus=0),
				)

	def test_clearing_the_end_date_is_blocked(self):
		with self.assertRaises(frappe.ValidationError):
			lock.check_rows_unchanged(contract([row()], docstatus=0, end_date=None), contract([row()], docstatus=0))

	def test_dates_of_a_contract_without_a_request_stay_editable(self):
		lock.check_rows_unchanged(
			contract([], docstatus=0, utility_service_request=None, start_date=date(2026, 11, 1), end_date=None),
			contract([], docstatus=0, utility_service_request=None),
		)
