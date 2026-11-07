"""Tests for the readers of a lease that follow Released On, under Item Price.

A row released on its Contract holds its property up to and including its
Released On, and nothing at all without one, in portal availability, the portal
lease states, the daily backstop that frees ended leases, and the Tenancy
Summary report.

Every test runs in a savepoint rolled back afterwards.
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, add_months, get_last_day, getdate, today

from utility_billing.api.portal import booking_core
from utility_billing.api.portal.booking_payload import serialise_request
from utility_billing.api.portal.properties import ACTIVE, HISTORY, classify_lease_item
from utility_billing.utility_billing.report.tenancy_summary import tenancy_summary
from utility_billing.utility_billing.tests import lease_fixtures as fx
from utility_billing.utility_billing.utils import availability, lease_status
from utility_billing.utility_billing.utils.property_status import release_ended_leases

P1 = "_Test Release Reader P1"
START = getdate(add_months(today(), -2)).replace(day=1)
END = getdate(add_months(START, 12))
YESTERDAY = getdate(add_days(today(), -1))
LATER = getdate(add_days(today(), 10))


class ReleasedCase(fx.SavepointMixin, FrappeTestCase):
	"""P1 leased by U1 for a year from two months ago, on a signed Contract, then released."""

	def setUp(self):
		super().setUp()
		fx.use_approach("Item Price")
		fx.lease_property(P1)
		self.u1 = fx.make_request([(P1, START, END)], START, END)
		self.contract = fx.make_contract(self.u1.name)

	def release(self, released_on):
		fx.release_rows(self.contract, 0, released_on=released_on)
		if not released_on:
			frappe.db.set_value("Contract Utility Property Item", self.contract.properties[0].name, "released_on", None)
		self.contract.reload()

	def held(self, day=None):
		return P1 in availability.get_held_properties(day, [P1])

	def allocation(self):
		payload = serialise_request(
			frappe.get_doc("Utility Service Request", self.u1.name),
			contract=frappe.db.get_value("Contract", self.contract.name, ["*"], as_dict=True),
			contract_rows=lease_status.get_contract_rows([self.contract.name])[self.contract.name],
		)
		return payload["properties"][0]

	def lease_state(self):
		contract = lease_status.get_contracts_by_request([self.u1.name])[self.u1.name]
		rows = lease_status.get_contract_rows([contract.name])[contract.name]
		return lease_status.derive_lease_status(1, contract, rows)

	def tenant_state(self):
		row = self.contract.properties[0]
		return classify_lease_item(row.is_active, row.end_date, 1, start_date=row.start_date, released_on=row.released_on)

	def summary(self, **filters):
		columns, data, *_rest = tenancy_summary.execute({"property": P1, **filters})
		return [column["fieldname"] for column in columns], [row for row in data if row["property"] == P1]


class TestReleasedBeforeToday(ReleasedCase):
	def setUp(self):
		super().setUp()
		self.release(YESTERDAY)

	def test_the_property_can_be_booked(self):
		self.assertFalse(self.held())
		self.assertTrue(availability.is_property_available(P1))
		booking_core.assert_bookable(booking_core.get_property_doc(P1))

	def test_the_portal_shows_it_released_and_ended(self):
		allocation = self.allocation()
		self.assertEqual((allocation["allocation_status"], allocation["released_on"]), ("Released", YESTERDAY))
		self.assertEqual(self.lease_state(), lease_status.EXPIRED)
		self.assertEqual(self.tenant_state(), HISTORY)

	def test_the_report_ends_it_on_its_release(self):
		fieldnames, rows = self.summary()
		self.assertIn("released_on", fieldnames)
		self.assertEqual((rows[0]["released_on"], rows[0]["remaining_days"]), (YESTERDAY, -1))
		self.assertEqual(self.summary(property_status="Active")[1], [])
		self.assertEqual(len(self.summary(property_status="Inactive")[1]), 1)


class TestReleasedAfterToday(ReleasedCase):
	def setUp(self):
		super().setUp()
		self.release(LATER)

	def test_the_property_is_held_until_its_release(self):
		self.assertTrue(self.held())
		with self.assertRaisesRegex(frappe.ValidationError, "already reserved until"):
			booking_core.assert_bookable(booking_core.get_property_doc(P1))

	def test_it_can_be_booked_from_the_day_after(self):
		self.assertTrue(self.held(LATER))
		self.assertFalse(self.held(add_days(LATER, 1)))

	def test_the_portal_keeps_it_live_until_then(self):
		self.assertEqual(frappe.db.get_value("Contract", self.contract.name, "status"), "Inactive")
		self.assertEqual(self.allocation()["allocation_status"], "Active")
		self.assertEqual(self.lease_state(), lease_status.ACTIVE)
		self.assertEqual(self.tenant_state(), ACTIVE)

	def test_the_report_counts_its_days_to_the_release(self):
		_fieldnames, rows = self.summary()
		self.assertEqual(rows[0]["remaining_days"], 10)
		self.assertEqual(len(self.summary(property_status="Active")[1]), 1)


class TestReleasedWithoutDate(ReleasedCase):
	def setUp(self):
		super().setUp()
		self.release(None)

	def test_it_holds_nothing(self):
		self.assertFalse(self.held())
		self.assertEqual(self.allocation()["allocation_status"], "Released")
		self.assertEqual(self.lease_state(), lease_status.EXPIRED)
		self.assertEqual(self.tenant_state(), HISTORY)
		self.assertIsNone(self.summary()[1][0]["remaining_days"])


class TestReleasedThenLeasedAgain(ReleasedCase):
	def setUp(self):
		super().setUp()
		self.release(YESTERDAY)

	def test_a_new_lease_holds_the_property_again(self):
		fx.make_request([(P1, today(), add_months(today(), 3))], today(), add_months(today(), 3))

		self.assertTrue(self.held())
		with self.assertRaisesRegex(frappe.ValidationError, "already reserved until"):
			booking_core.assert_bookable(booking_core.get_property_doc(P1))

	def test_the_backstop_never_frees_a_property_leased_again(self):
		fx.make_request([(P1, today(), add_months(today(), 3))], today(), add_months(today(), 3))
		frappe.db.set_value("Utility Property", P1, "status", "Occupied")

		with patch("utility_billing.utility_billing.utils.property_status.set_released_contracts_inactive"):
			release_ended_leases()

		self.assertEqual(fx.property_status(P1), "Occupied")


class TestSeveralRequests(ReleasedCase):
	"""U1 released early; U2 then leased P1 and ended last month."""

	def test_the_backstop_frees_the_property_once_every_lease_ended(self):
		released_on = getdate(add_days(START, 5))
		self.release(released_on)
		last_month_end = getdate(get_last_day(add_months(today(), -1)))
		u2_start = getdate(add_days(released_on, 1))
		# The request's own dates run in whole months, past its row
		fx.make_request([(P1, u2_start, last_month_end)], u2_start, add_months(u2_start, 2))
		frappe.db.set_value("Utility Property", P1, "status", "Occupied")

		with patch("utility_billing.utility_billing.utils.property_status.set_released_contracts_inactive"):
			freed = release_ended_leases()

		self.assertIn(P1, freed)
		self.assertEqual(fx.property_status(P1), "Available")
