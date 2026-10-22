"""Tests for the daily job releasing properties whose lease has ended.

Leases are written straight to the database so that each test controls the
exact row and header dates, the docstatus and the active flag of a request,
without the date rewriting done when a request is validated.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, add_months, today

from utility_billing.utility_billing.tests import factories
from utility_billing.utility_billing.utils.property_status import release_ended_leases

PROPERTY = "_Test Lease End Property"
CUSTOMER = "_Test Lease End Customer"

ENDED = add_days(today(), -3)
STARTED = add_months(today(), -6)
NOT_STARTED = add_months(today(), 3)
NOT_ENDED = add_months(today(), 6)


class TestReleaseEndedLeases(FrappeTestCase):
	"""Which held properties the daily job sets back to Available."""

	def setUp(self):
		super().setUp()
		factories.ensure_customer(CUSTOMER)
		factories.ensure_property(PROPERTY)
		frappe.db.savepoint("test_property_status")

	def tearDown(self):
		frappe.db.rollback(save_point="test_property_status")
		super().tearDown()

	def test_property_whose_lease_ended_is_released(self):
		self._lease(row_end=ENDED)

		self.assertIn(PROPERTY, release_ended_leases())
		self.assertEqual(self._status(), "Available")

	def test_header_end_date_is_used_when_the_row_has_none(self):
		self._lease(row_end=None, header_end=ENDED)

		self.assertIn(PROPERTY, release_ended_leases())
		self.assertEqual(self._status(), "Available")

	def test_open_ended_lease_keeps_the_property(self):
		self._lease(row_end=None, header_end=None)

		self.assertNotIn(PROPERTY, release_ended_leases())
		self.assertEqual(self._status(), "Occupied")

	def test_renewal_not_started_yet_keeps_the_property(self):
		self._lease(row_end=ENDED)
		self._lease(row_start=NOT_STARTED, row_end=add_months(NOT_STARTED, 3))

		self.assertNotIn(PROPERTY, release_ended_leases())
		self.assertEqual(self._status(), "Occupied")

	def test_property_is_released_once_every_lease_ended(self):
		self._lease(row_start=add_months(STARTED, -6), row_end=add_days(STARTED, -1))
		self._lease(row_end=ENDED)

		self.assertIn(PROPERTY, release_ended_leases())
		self.assertEqual(self._status(), "Available")

	def test_inactive_lease_does_not_keep_the_property(self):
		self._lease(row_end=ENDED)
		self._lease(row_end=NOT_ENDED, is_active=0)

		self.assertIn(PROPERTY, release_ended_leases())
		self.assertEqual(self._status(), "Available")

	def test_reserved_property_is_released(self):
		frappe.db.set_value("Utility Property", PROPERTY, "status", "Reserved")
		self._lease(row_end=ENDED)

		self.assertIn(PROPERTY, release_ended_leases())
		self.assertEqual(self._status(), "Available")

	def test_cancelled_lease_is_ignored(self):
		self._lease(row_end=ENDED, docstatus=2)

		self.assertNotIn(PROPERTY, release_ended_leases())
		self.assertEqual(self._status(), "Occupied")

	def test_property_under_maintenance_is_left_alone(self):
		frappe.db.set_value("Utility Property", PROPERTY, "status", "Under Maintenance")
		self._lease(row_end=ENDED)

		self.assertNotIn(PROPERTY, release_ended_leases())
		self.assertEqual(self._status(), "Under Maintenance")

	def test_lease_ending_today_has_not_ended(self):
		self._lease(row_end=today())

		self.assertNotIn(PROPERTY, release_ended_leases())
		self.assertEqual(self._status(), "Occupied")

	def _lease(self, row_end, row_start=STARTED, header_end=None, is_active=1, docstatus=1):
		"""Write a Utility Service Request leasing the test property."""
		request = frappe.new_doc("Utility Service Request")
		request.customer = CUSTOMER
		request.company = frappe.db.get_value("Company", {}, "name")
		request.start_date = row_start
		request.end_date = header_end
		request.docstatus = docstatus
		request.db_insert()

		row = request.append(
			"requested_properties",
			{
				"utility_property": PROPERTY,
				"start_date": row_start,
				"end_date": row_end,
				"is_active": is_active,
			},
		)
		row.parent = request.name
		row.docstatus = docstatus
		row.db_insert()

		return request

	def _status(self):
		return frappe.db.get_value("Utility Property", PROPERTY, "status")
