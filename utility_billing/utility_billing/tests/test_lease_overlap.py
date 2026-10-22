"""Tests for the overlapping lease check of the Utility Service Request.

The submitted leases of other requests are supplied by patching
``get_submitted_leases``, so these tests never write to the database: the
rules and the submit hooks are exercised on unsaved documents.
"""

from unittest.mock import patch

import frappe
from frappe.tests import UnitTestCase

from utility_billing.utility_billing.utils.lease_overlap import (
	periods_overlap,
	validate_no_overlapping_leases,
)

LEASES = "utility_billing.utility_billing.utils.lease_overlap.get_submitted_leases"


def lease(service_request, customer, start, end):
	return frappe._dict(service_request=service_request, customer=customer, start=start, end=end)


def request(rows, start="2026-10-01", end=None, name="UT-SER-REQ-TEST"):
	"""Return a request-like document with ``rows`` as its requested properties."""
	return frappe._dict(
		name=name,
		start_date=start,
		end_date=end,
		requested_properties=[
			frappe._dict({"idx": idx, "is_active": 1, **row}) for idx, row in enumerate(rows, start=1)
		],
	)


class TestPeriodsOverlap(UnitTestCase):
	"""Inclusive period overlap, with open ended and unbounded edges."""

	def test_disjoint_periods_do_not_overlap(self):
		self.assertFalse(periods_overlap("2026-01-01", "2026-03-31", "2026-04-01", "2026-06-30"))
		self.assertFalse(periods_overlap("2026-04-01", "2026-06-30", "2026-01-01", "2026-03-31"))

	def test_shared_boundary_day_overlaps(self):
		# The end date is a leased day, so a renewal starting on it overlaps.
		self.assertTrue(periods_overlap("2026-09-01", "2026-12-01", "2026-12-01", "2027-12-01"))

	def test_contained_period_overlaps(self):
		self.assertTrue(periods_overlap("2026-01-01", "2026-12-31", "2026-05-01", "2026-05-31"))

	def test_open_ended_lease_overlaps_every_later_lease(self):
		self.assertTrue(periods_overlap("2026-01-01", None, "2030-01-01", "2030-12-31"))
		self.assertFalse(periods_overlap("2026-01-01", None, "2025-01-01", "2025-12-31"))

	def test_blank_start_is_unbounded(self):
		self.assertTrue(periods_overlap(None, "2026-06-30", "2020-01-01", "2020-01-31"))

	def test_two_open_ended_leases_overlap(self):
		self.assertTrue(periods_overlap("2026-01-01", None, "2027-01-01", None))


class TestOverlappingLeaseCheck(UnitTestCase):
	"""The per-row check against other submitted leases and the request itself."""

	def test_lease_of_another_customer_blocks_the_request(self):
		doc = request([{"utility_property": "House-1", "start_date": "2026-10-01", "end_date": "2027-10-01"}])

		with patch(LEASES, return_value=[lease("UT-OTHER", "Other Customer", "2026-09-01", "2026-12-01")]):
			with self.assertRaises(frappe.ValidationError) as raised:
				validate_no_overlapping_leases(doc)

		message = str(raised.exception)
		for expected in ("House-1", "row 1", "Other Customer", "UT-OTHER", "2026-09-01", "2026-12-01"):
			self.assertIn(expected, message)

	def test_lease_of_the_same_customer_also_blocks_the_request(self):
		doc = request([{"utility_property": "House-1", "start_date": "2026-10-02", "end_date": "2027-10-02"}])

		with patch(LEASES, return_value=[lease("UT-OTHER", "Same Customer", "2026-09-01", "2028-12-01")]):
			with self.assertRaises(frappe.ValidationError):
				validate_no_overlapping_leases(doc)

	def test_lease_that_does_not_overlap_is_allowed(self):
		doc = request([{"utility_property": "House-1", "start_date": "2027-01-01", "end_date": "2027-12-31"}])

		with patch(LEASES, return_value=[lease("UT-OTHER", "Other Customer", "2026-01-01", "2026-12-31")]):
			validate_no_overlapping_leases(doc)

	def test_only_the_conflicting_row_is_reported(self):
		doc = request(
			[
				{"utility_property": "House-1", "start_date": "2026-10-01", "end_date": "2027-10-01"},
				{"utility_property": "House-2", "start_date": "2026-10-01", "end_date": "2027-10-01"},
			]
		)
		taken = {"House-2": [lease("UT-OTHER", "Other Customer", "2026-09-01", "2026-12-01")]}

		with patch(LEASES, side_effect=lambda prop, exclude=None: taken.get(prop, [])):
			with self.assertRaises(frappe.ValidationError) as raised:
				validate_no_overlapping_leases(doc)

		self.assertIn("House-2", str(raised.exception))
		self.assertIn("row 2", str(raised.exception))
		self.assertNotIn("House-1", str(raised.exception))

	def test_row_without_dates_uses_the_request_dates(self):
		# The row has no dates of its own, so the request's open ended lease applies.
		doc = request([{"utility_property": "House-1"}], start="2026-10-01", end=None)

		with patch(LEASES, return_value=[lease("UT-OTHER", "Other Customer", "2030-01-01", "2030-12-31")]):
			with self.assertRaises(frappe.ValidationError):
				validate_no_overlapping_leases(doc)

	def test_inactive_row_has_released_its_property(self):
		doc = request([{"utility_property": "House-1", "start_date": "2026-10-01", "is_active": 0}])

		with patch(LEASES, return_value=[lease("UT-OTHER", "Other Customer", "2026-09-01", None)]) as leases:
			validate_no_overlapping_leases(doc)

		leases.assert_not_called()

	def test_same_property_requested_twice_for_overlapping_dates(self):
		doc = request(
			[
				{"utility_property": "House-1", "start_date": "2026-10-01", "end_date": "2027-03-31"},
				{"utility_property": "House-1", "start_date": "2027-03-01", "end_date": "2027-10-01"},
			]
		)

		with patch(LEASES, return_value=[]):
			with self.assertRaises(frappe.ValidationError) as raised:
				validate_no_overlapping_leases(doc)

		self.assertIn("rows 1 and 2", str(raised.exception))

	def test_the_request_itself_is_excluded_from_the_lookup(self):
		doc = request([{"utility_property": "House-1", "start_date": "2026-10-01"}], name="UT-SELF")

		with patch(LEASES, return_value=[]) as leases:
			validate_no_overlapping_leases(doc)

		leases.assert_called_once_with("House-1", exclude="UT-SELF")

	def test_open_ended_existing_lease_blocks_any_later_lease(self):
		doc = request([{"utility_property": "House-1", "start_date": "2031-01-01", "end_date": "2031-12-31"}])

		with patch(LEASES, return_value=[lease("UT-OTHER", "Other Customer", "2026-01-01", None)]):
			with self.assertRaises(frappe.ValidationError) as raised:
				validate_no_overlapping_leases(doc)

		self.assertIn("with no end date", str(raised.exception))


class TestSubmitHooks(UnitTestCase):
	"""The check runs when a request is submitted and when it is updated after submit."""

	def _unsaved_request(self):
		return frappe.get_doc(
			{
				"doctype": "Utility Service Request",
				"start_date": "2026-10-01",
				"requested_properties": [
					{"utility_property": "House-1", "start_date": "2026-10-01", "end_date": "2027-10-01", "is_active": 1}
				],
			}
		)

	def test_submitting_an_overlapping_request_is_blocked(self):
		doc = self._unsaved_request()

		with patch(LEASES, return_value=[lease("UT-OTHER", "Other Customer", "2026-09-01", "2026-12-01")]):
			with self.assertRaises(frappe.ValidationError):
				doc.run_method("before_submit")

	def test_submitting_a_free_property_is_allowed(self):
		doc = self._unsaved_request()

		with patch(LEASES, return_value=[]):
			doc.run_method("before_submit")

	def test_editing_a_submitted_request_into_an_overlap_is_blocked(self):
		doc = self._unsaved_request()

		with patch(LEASES, return_value=[lease("UT-OTHER", "Other Customer", "2026-09-01", "2026-12-01")]):
			with self.assertRaises(frappe.ValidationError):
				doc.run_method("before_update_after_submit")
