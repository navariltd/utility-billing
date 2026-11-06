"""Tests for the Utility Service Request of each Sales Invoice line, under Item Price.

Covers the resolution rules of ``line_request``: by property and date, by date
among requests without a property, the user's pick between several, and the
blocks; the header of a draft moved onto its lines; and the API the form uses.
Invoices are unsaved and governed through the hook functions.
"""

from unittest import skipUnless

import frappe
from frappe.tests.utils import FrappeTestCase

from utility_billing.api import sales_invoice as invoice_api
from utility_billing.utility_billing.doctype.utility_service_request.utility_service_request import (
	fill_request_line,
)
from utility_billing.utility_billing.overrides.server import sales_invoice
from utility_billing.utility_billing.tests import lease_fixtures as fx
from utility_billing.utility_billing.tests.line_request_fixtures import (
	ELECTRICITY,
	OTHER_CUSTOMER,
	OTHER_ITEM,
	P1,
	P2,
	make_invoice,
	make_price,
	make_request,
	setup_items,
)


def has_line_column() -> bool:
	return frappe.db.has_column("Sales Invoice Item", "utility_service_request")


class LineRequestCase(fx.SavepointMixin, FrappeTestCase):
	"""P1 leased by U1 (January to June 2027) then U2 (July to December), P2 by U3 all year.

	U1 and U3 list Electricity at 200 and 250.
	"""

	def setUp(self):
		super().setUp()
		fx.use_approach("Item Price")
		setup_items()
		self.u1 = make_request([(P1, "2027-01-01", "2027-06-30")], "2027-01-01", "2027-07-01", [(ELECTRICITY, 200)])
		self.u2 = make_request([(P1, "2027-07-01", "2027-12-31")], "2027-07-01", "2028-01-01")
		self.u3 = make_request([(P2, "2027-01-01", "2027-12-31")], "2027-01-01", "2028-01-01", [(ELECTRICITY, 250)])
		make_price(P1, 1000, "2027-01-01", "2027-06-30")
		make_price(P1, 1200, "2027-07-01", "2027-12-31")
		make_price(P2, 2000, "2027-01-01", "2027-12-31")

	def govern(self, invoice):
		return sales_invoice.govern_utility_lines(invoice)

	def requests(self, invoice):
		return [row.get("utility_service_request") for row in invoice.items]


class TestByProperty(LineRequestCase):
	def test_two_requests_for_one_property_in_different_periods(self):
		march = make_invoice([{"item_code": P1}], "2027-03-10")
		september = make_invoice([{"item_code": P1}], "2027-09-10")

		self.govern(march)
		self.govern(september)

		self.assertEqual((self.requests(march), march.items[0].rate), ([self.u1.name], 1000))
		self.assertEqual((self.requests(september), september.items[0].rate), ([self.u2.name], 1200))
		self.assertIsNone(march.utility_service_request)

	def test_one_invoice_bills_a_property_across_both_requests(self):
		invoice = make_invoice(
			[{"item_code": P1, "custom_posting_date": "2027-06-01"}, {"item_code": P1, "custom_posting_date": "2027-07-01"}],
			"2027-06-01",
		)

		self.govern(invoice)

		self.assertEqual(self.requests(invoice), [self.u1.name, self.u2.name])
		self.assertEqual([row.rate for row in invoice.items], [1000, 1200])

	def test_an_invoice_with_two_properties_from_two_requests(self):
		invoice = make_invoice([{"item_code": P1}, {"item_code": P2}], "2027-03-10")

		governed = self.govern(invoice)

		self.assertEqual(self.requests(invoice), [self.u1.name, self.u3.name])
		self.assertEqual([row.utility_property for row in invoice.items], [P1, P2])
		self.assertEqual([row.rate for row in invoice.items], [1000, 2000])
		self.assertEqual([entry.service_request for entry in governed], [self.u1.name, self.u3.name])

	def test_electricity_with_a_chosen_property(self):
		invoice = make_invoice(
			[
				{"item_code": ELECTRICITY, "utility_property": P1, "rate": 200},
				{"item_code": ELECTRICITY, "utility_property": P2, "rate": 250},
			],
			"2027-03-10",
		)

		self.govern(invoice)

		self.assertEqual(self.requests(invoice), [self.u1.name, self.u3.name])
		self.assertEqual([row.rate for row in invoice.items], [200, 250])

	def test_electricity_without_a_property_asks_for_one(self):
		invoice = make_invoice([{"item_code": ELECTRICITY}], "2027-03-10")

		with self.assertRaisesRegex(frappe.ValidationError, "Pick the property on this line"):
			self.govern(invoice)

	def test_a_property_not_leased_on_the_date_is_blocked(self):
		invoice = make_invoice([{"item_code": P2}], "2028-02-10")

		with self.assertRaisesRegex(frappe.ValidationError, "No Utility Service Request of .* leases"):
			self.govern(invoice)

	def test_the_rate_never_chooses_the_request(self):
		invoice = make_invoice([{"item_code": P1, "rate": 1200, "price_list_rate": 1200}], "2027-03-10")

		self.govern(invoice)

		self.assertEqual((self.requests(invoice), invoice.items[0].rate), ([self.u1.name], 1000))

	def test_a_request_set_by_hand_on_a_derived_line_is_replaced(self):
		invoice = make_invoice([{"item_code": P1, "utility_service_request": self.u2.name}], "2027-03-10")

		self.govern(invoice)

		self.assertEqual(self.requests(invoice), [self.u1.name])


class TestReleasedRows(LineRequestCase):
	def test_a_row_released_on_the_contract_leases_nothing(self):
		fx.release_rows(fx.make_contract(self.u3.name), 0)
		invoice = make_invoice([{"item_code": P2}], "2027-03-10")

		with self.assertRaisesRegex(frappe.ValidationError, "leases"):
			self.govern(invoice)

	def test_a_row_released_on_the_request_leases_nothing(self):
		frappe.db.set_value(
			"Contract Utility Property Item", self.u3.requested_properties[0].name, "is_active", 0
		)
		invoice = make_invoice([{"item_code": P2}], "2027-03-10")

		with self.assertRaisesRegex(frappe.ValidationError, "leases"):
			self.govern(invoice)


class TestWithoutProperty(fx.SavepointMixin, FrappeTestCase):
	"""Requests of another customer listing Electricity without any property."""

	def setUp(self):
		super().setUp()
		fx.use_approach("Item Price")
		setup_items()
		self.n1 = make_request([], "2027-01-01", "2027-07-01", [(ELECTRICITY, 200)], customer=OTHER_CUSTOMER)
		self.n2 = make_request([], "2027-07-01", "2028-01-01", [(ELECTRICITY, 300)], customer=OTHER_CUSTOMER)

	def invoice(self, posting_date, rate=200, **line):
		return make_invoice([{"item_code": ELECTRICITY, "rate": rate, **line}], posting_date, customer=OTHER_CUSTOMER)

	def test_one_request_covering_the_date_is_used(self):
		invoice = self.invoice("2027-03-10")

		sales_invoice.govern_utility_lines(invoice)

		self.assertEqual((invoice.items[0].utility_service_request, invoice.items[0].rate), (self.n1.name, 200))

	def test_overlapping_requests_let_the_user_pick(self):
		n3 = make_request([], "2027-01-01", "2028-01-01", [(ELECTRICITY, 400)], customer=OTHER_CUSTOMER)

		with self.assertRaisesRegex(frappe.ValidationError, "Several Utility Service Requests cover"):
			sales_invoice.govern_utility_lines(self.invoice("2027-03-10"))

		picked = self.invoice("2027-03-10", rate=400, utility_service_request=n3.name)
		sales_invoice.govern_utility_lines(picked)
		self.assertEqual((picked.items[0].utility_service_request, picked.items[0].rate), (n3.name, 400))

	def test_a_pick_outside_the_candidates_is_refused(self):
		make_request([], "2027-01-01", "2028-01-01", [(ELECTRICITY, 400)], customer=OTHER_CUSTOMER)

		with self.assertRaisesRegex(frappe.ValidationError, "Several"):
			sales_invoice.govern_utility_lines(self.invoice("2027-03-10", utility_service_request=self.n2.name))

	def test_no_request_covering_the_date_says_so(self):
		with self.assertRaisesRegex(frappe.ValidationError, "without a property covers"):
			sales_invoice.govern_utility_lines(self.invoice("2028-03-10"))

	def test_mixed_candidates_use_the_requests_without_a_property(self):
		make_request([(P1, "2027-01-01", "2027-12-31")], "2027-01-01", "2028-01-01", [(ELECTRICITY, 999)], customer=OTHER_CUSTOMER)
		make_price(P1, 1000, "2027-01-01", "2027-12-31", customer=OTHER_CUSTOMER)

		invoice = self.invoice("2027-03-10")
		sales_invoice.govern_utility_lines(invoice)

		self.assertEqual(invoice.items[0].utility_service_request, self.n1.name)


class TestHeaderMovedToLines(LineRequestCase):
	def test_a_draft_header_is_moved_onto_its_governed_lines(self):
		invoice = make_invoice(
			[{"item_code": P1}, {"item_code": ELECTRICITY, "rate": 200}, {"item_code": OTHER_ITEM, "rate": 5}],
			"2027-03-10",
			header=self.u1.name,
		)

		self.govern(invoice)

		self.assertIsNone(invoice.utility_service_request)
		self.assertEqual(self.requests(invoice), [self.u1.name, self.u1.name, None])
		# The request has one property, so its Electricity line bills it
		self.assertEqual(invoice.items[1].utility_property, P1)
		self.assertEqual([row.rate for row in invoice.items], [1000, 200, 5])

	def test_a_header_with_several_properties_asks_for_the_property(self):
		both = make_request(
			[(P1, "2028-01-01", "2028-12-31"), (P2, "2028-01-01", "2028-12-31")],
			"2028-01-01",
			"2029-01-01",
			[(ELECTRICITY, 300)],
		)
		invoice = make_invoice([{"item_code": ELECTRICITY}], "2028-03-10", header=both.name)

		with self.assertRaisesRegex(frappe.ValidationError, "Pick the property on this line"):
			self.govern(invoice)

	def test_an_ordinary_line_carries_no_request(self):
		invoice = make_invoice([{"item_code": OTHER_ITEM, "rate": 5, "utility_service_request": self.u1.name}], "2027-03-10")

		self.govern(invoice)

		self.assertIsNone(invoice.items[0].get("utility_service_request"))


class TestFormApi(LineRequestCase):
	def test_the_form_gets_each_line_resolved_without_saving(self):
		invoice = make_invoice([{"item_code": P1}, {"item_code": ELECTRICITY}], "2027-03-10")
		for index, row in enumerate(invoice.items):
			row.name = f"new-line-{index}"

		result = invoice_api.resolve_invoice_lines(invoice.as_dict())

		self.assertFalse(result["header_path"])
		first, second = result["rows"]["new-line-0"], result["rows"]["new-line-1"]
		self.assertEqual((first.status, first.service_request, first.role), ("resolved", self.u1.name, "primary"))
		self.assertEqual(second.status, "pick_property")
		self.assertIn("Pick the property on this line", second.message)

	def test_an_auto_repeat_draft_keeps_its_header_in_the_form(self):
		invoice = make_invoice([{"item_code": P1}], "2027-03-10", header=self.u1.name, auto_repeat="_Test AR")
		invoice.items[0].name = "new-line-0"

		result = invoice_api.resolve_invoice_lines(invoice.as_dict())

		self.assertTrue(result["header_path"])
		self.assertEqual(result["rows"]["new-line-0"]["service_request"], self.u1.name)


class TestInvoiceFromRequest(LineRequestCase):
	def test_lines_made_from_a_request_get_its_request_and_property(self):
		invoice = make_invoice([{"item_code": P1}, {"item_code": ELECTRICITY, "rate": 200}], "2027-03-10")
		for row in invoice.items:
			fill_request_line(row, self.u1.name)

		self.assertEqual([(row.utility_service_request, row.utility_property) for row in invoice.items], [(self.u1.name, P1), (self.u1.name, P1)])

		self.govern(invoice)
		self.assertEqual([row.rate for row in invoice.items], [1000, 200])


@skipUnless(has_line_column(), "needs the line field, which a migrate adds")
class TestAfterMigrate(LineRequestCase):
	def test_the_request_lists_invoices_found_through_their_lines(self):
		invoice = make_invoice([{"item_code": P1}], "2027-03-10", set_posting_time=1)
		invoice.flags.ignore_mandatory = True
		invoice.insert(ignore_permissions=True)

		self.assertIn(invoice.name, [row.name for row in invoice_api.get_request_invoices(self.u1.name)])
		self.assertNotIn(invoice.name, [row.name for row in invoice_api.get_request_invoices(self.u2.name)])

	def test_cancelling_a_request_on_a_submitted_line_is_refused(self):
		invoice = make_invoice([{"item_code": P1}], "2027-03-10", set_posting_time=1)
		invoice.insert(ignore_permissions=True)
		invoice.submit()

		with self.assertRaises(frappe.LinkExistsError):
			frappe.get_doc("Utility Service Request", self.u1.name).cancel()
