"""Tests for the Property Wise Invoicing report.

The month grid, the property resolution of invoice lines and the merge of both
are pure, so these tests need no database.
"""

from datetime import date

import frappe
from frappe.tests import UnitTestCase

from utility_billing.utility_billing.report.property_wise_invoicing import (
	property_wise_invoicing as report,
)

YEAR_START = date(2026, 1, 1)
YEAR_END = date(2026, 12, 31)
TODAY = date(2026, 10, 3)


def lease(property_name, customer, start, end, service_request="USR-1"):
	return frappe._dict(
		service_request=service_request,
		property=property_name,
		customer=customer,
		start=start,
		end=end,
	)


def line(item_code, customer, billing_date, amount, service_request=None):
	return frappe._dict(
		item_code=item_code,
		customer=customer,
		service_request=service_request,
		billing_date=billing_date,
		amount=amount,
	)


class TestLeaseGrid(UnitTestCase):
	"""Which property months get a row."""

	def test_every_leased_month_up_to_the_current_one_is_reported(self):
		grid = report.build_lease_grid(
			[lease("P1", "C1", date(2026, 7, 15), date(2027, 6, 30))], YEAR_START, YEAR_END, TODAY
		)

		self.assertEqual(
			sorted(month for _, _, month in grid),
			[date(2026, 7, 1), date(2026, 8, 1), date(2026, 9, 1), date(2026, 10, 1)],
		)
		self.assertEqual(set(grid.values()), {date(2027, 6, 30)})

	def test_months_after_the_lease_end_are_not_reported(self):
		grid = report.build_lease_grid(
			[lease("P1", "C1", date(2026, 2, 1), date(2026, 4, 10))], YEAR_START, YEAR_END, TODAY
		)

		self.assertEqual(
			sorted(month for _, _, month in grid),
			[date(2026, 2, 1), date(2026, 3, 1), date(2026, 4, 1)],
		)

	def test_open_ended_lease_runs_to_the_current_month(self):
		grid = report.build_lease_grid(
			[lease("P1", "C1", date(2026, 9, 1), None)], YEAR_START, YEAR_END, TODAY
		)

		self.assertEqual(list(grid), [("P1", "C1", date(2026, 9, 1)), ("P1", "C1", date(2026, 10, 1))])
		self.assertEqual(set(grid.values()), {None})

	def test_lease_ends_cover_the_whole_period_when_not_cut_at_today(self):
		grid = report.build_lease_grid(
			[lease("P1", "C1", date(2026, 11, 1), date(2027, 1, 31))], YEAR_START, YEAR_END, YEAR_END
		)

		self.assertEqual(sorted(month for _, _, month in grid), [date(2026, 11, 1), date(2026, 12, 1)])

	def test_months_outside_the_period_are_not_reported(self):
		grid = report.build_lease_grid(
			[lease("P1", "C1", date(2025, 11, 1), date(2027, 2, 28))],
			date(2026, 3, 1),
			date(2026, 3, 31),
			TODAY,
		)

		self.assertEqual(list(grid), [("P1", "C1", date(2026, 3, 1))])

	def test_lease_without_a_start_date_is_skipped(self):
		self.assertEqual(
			report.build_lease_grid([lease("P1", "C1", None, None)], YEAR_START, YEAR_END, TODAY), {}
		)

	def test_latest_end_wins_when_two_leases_cover_a_month(self):
		grid = report.build_lease_grid(
			[
				lease("P1", "C1", date(2026, 1, 1), date(2026, 3, 31)),
				lease("P1", "C1", date(2026, 3, 1), date(2026, 12, 31), service_request="USR-2"),
			],
			YEAR_START,
			YEAR_END,
			TODAY,
		)

		self.assertEqual(grid[("P1", "C1", date(2026, 3, 1))], date(2026, 12, 31))


class TestPropertyResolution(UnitTestCase):
	"""Which property an invoice line bills."""

	owners = {"ITEM-1": ["P1"], "SHARED": ["P1", "P2"]}

	def test_item_owned_by_one_property_bills_it(self):
		self.assertEqual(
			report.resolve_property(line("ITEM-1", "C1", date(2026, 5, 1), 10), self.owners, []), "P1"
		)

	def test_shared_item_bills_the_property_on_the_invoice_request(self):
		leases = [
			lease("P1", "C1", date(2026, 1, 1), None, service_request="USR-1"),
			lease("P2", "C1", date(2026, 1, 1), None, service_request="USR-2"),
		]

		resolved = report.resolve_property(
			line("SHARED", "C1", date(2026, 5, 1), 10, service_request="USR-2"), self.owners, leases
		)

		self.assertEqual(resolved, "P2")

	def test_shared_item_falls_back_to_the_lease_covering_the_date(self):
		leases = [
			lease("P1", "C1", date(2026, 1, 1), date(2026, 3, 31), service_request="USR-1"),
			lease("P2", "C1", date(2026, 4, 1), None, service_request="USR-2"),
		]

		resolved = report.resolve_property(
			line("SHARED", "C1", date(2026, 5, 1), 10, service_request="USR-OTHER"), self.owners, leases
		)

		self.assertEqual(resolved, "P2")

	def test_lease_of_another_customer_does_not_resolve(self):
		leases = [lease("P1", "C2", date(2026, 1, 1), None)]

		self.assertIsNone(
			report.resolve_property(line("SHARED", "C1", date(2026, 5, 1), 10), self.owners, leases)
		)

	def test_shared_item_outside_any_lease_is_unresolved(self):
		lines = [line("SHARED", "C1", date(2026, 6, 23), 100), line("SHARED", "C1", date(2026, 6, 24), 50)]

		invoiced = report.resolve_lines(lines, self.owners, [])

		self.assertEqual(invoiced, {(report.unresolved_label("SHARED"), "C1", date(2026, 6, 1)): 150})


class TestMergeAndTotals(UnitTestCase):
	"""How invoiced amounts meet the lease grid."""

	def test_invoiced_amounts_are_summed_per_property_customer_and_month(self):
		lines = [
			line("ITEM-1", "C1", date(2026, 9, 1), 100),
			line("ITEM-1", "C1", date(2026, 9, 30), 50),
			line("ITEM-1", "C1", date(2026, 10, 1), 70),
		]

		invoiced = report.resolve_lines(lines, {"ITEM-1": ["P1"]}, [])

		self.assertEqual(invoiced, {("P1", "C1", date(2026, 9, 1)): 150, ("P1", "C1", date(2026, 10, 1)): 70})

	def test_leased_month_without_invoice_shows_zero(self):
		key = ("P1", "C1", date(2026, 9, 1))

		rows = report.merge({key: date(2027, 1, 1)}, {}, {key: date(2027, 1, 1)})

		self.assertEqual(rows[0].invoiced_amount, 0)
		self.assertEqual(rows[0].lease_expires, date(2027, 1, 1))

	def test_invoiced_month_outside_any_lease_has_no_lease_end(self):
		rows = report.merge({}, {("P1", "C1", date(2026, 6, 1)): 125}, {})

		self.assertEqual(rows[0].invoiced_amount, 125)
		self.assertIsNone(rows[0].lease_expires)

	def test_invoiced_month_after_today_keeps_its_lease_end(self):
		key = ("P1", "C1", date(2026, 11, 1))

		rows = report.merge({}, {key: 75}, {key: date(2026, 12, 1)})

		self.assertEqual(rows[0].lease_expires, date(2026, 12, 1))

	def test_another_customer_billed_in_a_leased_month_gets_its_own_row(self):
		month = date(2026, 9, 1)

		rows = report.merge({("P1", "C1", month): None}, {("P1", "C2", month): 40}, {("P1", "C1", month): None})

		self.assertEqual([(row.customer, row.invoiced_amount) for row in rows], [("C1", 0), ("C2", 40)])

	def test_rows_are_sorted_with_unresolved_items_last(self):
		unresolved = report.unresolved_label("SHARED")
		rows = report.merge(
			{},
			{
				(unresolved, "C1", date(2026, 1, 1)): 1,
				("P2", "C1", date(2026, 2, 1)): 2,
				("P1", "C1", date(2026, 3, 1)): 3,
				("P1", "C1", date(2026, 1, 1)): 4,
			},
			{},
		)

		self.assertEqual(
			[(row.property, row.month) for row in rows],
			[("P1", "Jan 2026"), ("P1", "Mar 2026"), ("P2", "Feb 2026"), (unresolved, "Jan 2026")],
		)

	def test_subtotal_follows_each_property_and_grand_total_closes(self):
		rows = report.merge(
			{},
			{
				("P1", "C1", date(2026, 1, 1)): 100,
				("P1", "C1", date(2026, 2, 1)): 50,
				("P2", "C1", date(2026, 1, 1)): 30,
			},
			{},
		)

		data = report.add_totals(rows)

		self.assertEqual(
			[(row.property, row.invoiced_amount, bool(row.get("is_total_row"))) for row in data],
			[
				("P1", 100, False),
				("P1", 50, False),
				("Total P1", 150, True),
				("P2", 30, False),
				("Total P2", 30, True),
				("Grand Total", 180, True),
			],
		)

	def test_no_rows_means_no_totals(self):
		self.assertEqual(report.add_totals([]), [])


class TestPeriod(UnitTestCase):
	"""The dates covered by the Year and Month filters."""

	def test_year_alone_covers_the_whole_year(self):
		self.assertEqual(report.get_period(frappe._dict(year=2026)), (YEAR_START, YEAR_END))

	def test_month_narrows_the_period_to_that_month(self):
		self.assertEqual(
			report.get_period(frappe._dict(year="2024", month="2")), (date(2024, 2, 1), date(2024, 2, 29))
		)

	def test_year_is_required(self):
		with self.assertRaises(frappe.ValidationError):
			report.get_period(frappe._dict())
