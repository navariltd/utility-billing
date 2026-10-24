"""Unit tests for the portal booking status and date helpers.

These tests use unsaved values only, so they never write to the database.
"""

import frappe
from frappe.tests import IntegrationTestCase, UnitTestCase
from frappe.utils import add_days, add_months, getdate, today

from utility_billing.api.portal.booking_core import get_booking_customer, normalise_dates
from utility_billing.api.portal.roles import get_portal_customers
from utility_billing.utility_billing.utils.lease_status import (
	ACTIVE,
	AWAITING_SIGNATURE,
	CANCELLED,
	CONTRACT_DRAFT,
	EXPIRED,
	RESERVED,
	derive_allocation_status,
	derive_lease_status,
)

CONTRACT = {
	"name": "CONTRACT-TEST",
	"docstatus": 1,
	"status": "Open",
	"is_signed": 1,
	"start_date": "2026-01-01",
	"end_date": "2026-12-31",
}


class TestLeaseStatus(UnitTestCase):
	"""Derived status of a request, its contract and its allocations."""

	def test_draft_and_cancelled_requests(self):
		self.assertEqual(derive_lease_status(0), "Draft")
		self.assertEqual(derive_lease_status(2), CANCELLED)

	def test_submitted_request_without_contract_is_reserved(self):
		self.assertEqual(derive_lease_status(1), RESERVED)

	def test_contract_state_drives_the_status(self):
		self.assertEqual(derive_lease_status(1, {**CONTRACT, "docstatus": 0}), CONTRACT_DRAFT)
		self.assertEqual(derive_lease_status(1, {**CONTRACT, "is_signed": 0}), AWAITING_SIGNATURE)
		self.assertEqual(derive_lease_status(1, {**CONTRACT, "status": "Inactive"}), EXPIRED)

	def test_live_allocation_is_active(self):
		rows = [{"is_active": 1, "start_date": "2026-01-01", "end_date": "2026-12-31"}]
		self.assertEqual(derive_lease_status(1, CONTRACT, rows, reference_date="2026-06-01"), ACTIVE)

	def test_ended_or_released_allocations_expire_the_lease(self):
		ended = [{"is_active": 1, "start_date": "2026-01-01", "end_date": "2026-03-01"}]
		released = [{"is_active": 0, "start_date": "2026-01-01", "end_date": "2026-12-31"}]

		self.assertEqual(derive_lease_status(1, CONTRACT, ended, reference_date="2026-06-01"), EXPIRED)
		self.assertEqual(
			derive_lease_status(1, CONTRACT, released, reference_date="2026-06-01"),
			EXPIRED,
		)

	def test_open_ended_allocation_stays_active(self):
		rows = [{"is_active": 1, "start_date": "2026-01-01", "end_date": None}]
		self.assertEqual(derive_lease_status(1, CONTRACT, rows, reference_date="2030-01-01"), ACTIVE)


class TestAllocationStatus(UnitTestCase):
	"""Per-property allocation labels used on the booking card."""

	def test_released_takes_precedence(self):
		self.assertEqual(derive_allocation_status(0, None, None), "Released")

	def test_dates_label_the_allocation(self):
		self.assertEqual(
			derive_allocation_status(1, "2026-01-01", "2026-03-01", reference_date="2026-06-01"),
			"Expired",
		)
		self.assertEqual(
			derive_allocation_status(1, "2026-07-01", "2026-12-31", reference_date="2026-06-01"),
			"Upcoming",
		)
		self.assertEqual(
			derive_allocation_status(1, "2026-01-01", "2026-12-31", reference_date="2026-06-01"),
			"Active",
		)


class TestNormaliseDates(UnitTestCase):
	"""Lease date validation shared by booking creation and changes."""

	def test_length_derives_the_end_date(self):
		start = add_days(today(), 10)
		start_date, end_date, months = normalise_dates(start, None, 6)

		self.assertEqual(start_date, getdate(start))
		self.assertEqual(end_date, add_months(getdate(start), 6))
		self.assertEqual(months, 6)

	def test_end_date_derives_the_length(self):
		start = add_days(today(), 10)
		end = add_months(start, 3)
		start_date, end_date, months = normalise_dates(start, end, None)

		self.assertEqual(start_date, getdate(start))
		self.assertEqual(end_date, getdate(end))
		self.assertEqual(months, 3)

	def test_defaults_to_a_full_year(self):
		start_date, end_date, months = normalise_dates(add_days(today(), 1))

		self.assertEqual(start_date, add_days(getdate(today()), 1))
		self.assertEqual(end_date, add_months(start_date, 12))
		self.assertEqual(months, 12)

	def test_past_and_inverted_dates_are_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			normalise_dates(add_days(today(), -1))
		with self.assertRaises(frappe.ValidationError):
			normalise_dates(add_days(today(), 10), add_days(today(), 5))


class TestPortalCustomerProvisioning(IntegrationTestCase):
	"""A first-time tenant gets a Customer instead of a 403 on booking."""

	def test_booking_customer_is_created_and_linked(self):
		email = f"portal-{frappe.generate_hash(length=8)}@example.com"
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": "Portal",
				"last_name": "Tenant",
				"send_welcome_email": 0,
			}
		).insert(ignore_permissions=True)

		frappe.set_user(user.name)
		try:
			customer = get_booking_customer()
		finally:
			frappe.set_user("Administrator")

		self.assertTrue(customer["name"])
		self.assertEqual(frappe.db.get_value("Customer", customer["name"], "email_id"), email)
		self.assertTrue(
			frappe.db.exists(
				"Portal User",
				{"parenttype": "Customer", "parent": customer["name"], "user": user.name},
			)
		)

		linked = get_portal_customers(user.name)
		self.assertEqual([entry["name"] for entry in linked], [customer["name"]])
