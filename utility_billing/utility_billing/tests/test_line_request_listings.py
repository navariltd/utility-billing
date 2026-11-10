"""Tests for the reports and portal pages listing invoices by Utility Service Request.

Each finds an invoice through its lines' requests, else its header's: old
invoices (header only), new ones (lines only), and one invoice billing lines of
two requests. Submitted invoices are written straight to the database inside
the savepoint; they need the line field's column, which a migrate adds.
"""

from unittest import skipUnless
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from utility_billing.api.portal.booking_payload import get_request_documents
from utility_billing.api.portal.property_vouchers import SALES_INVOICE_FIELDS, _get_vouchers
from utility_billing.utility_billing.report.property_billing_overview.property_billing_overview import (
	PropertyBillingOverview,
)
from utility_billing.utility_billing.report.property_wise_invoicing import property_wise_invoicing
from utility_billing.utility_billing.tests import lease_fixtures as fx
from utility_billing.utility_billing.tests.line_request_fixtures import P1, P2, make_request, setup_items
from utility_billing.utility_billing.tests.test_line_request import LineRequestCase, has_line_column
from utility_billing.utility_billing.tests.test_line_request_readers import submitted_invoice
from utility_billing.utility_billing.utils.line_request import invoice_requests


@skipUnless(has_line_column(), "needs the line field, which a migrate adds")
class ListingCase(LineRequestCase):
	def setUp(self):
		super().setUp()
		self.old = submitted_invoice([{"item_code": P1, "rate": 1000, "utility_property": P1}], "2027-03-01", header=self.u1.name)
		self.new = submitted_invoice(
			[{"item_code": P1, "rate": 1200, "utility_property": P1, "utility_service_request": self.u2.name}], "2027-08-01"
		)
		self.mixed = submitted_invoice(
			[
				{"item_code": P1, "rate": 1000, "utility_property": P1, "utility_service_request": self.u1.name},
				{"item_code": P2, "rate": 2000, "utility_property": P2, "utility_service_request": self.u3.name},
			],
			"2027-04-01",
		)


class TestInvoiceRequests(ListingCase):
	def test_old_new_and_mixed_invoices_are_found_by_their_requests(self):
		pairs = set(invoice_requests([self.u1.name, self.u2.name, self.u3.name]))

		self.assertEqual(
			pairs,
			{
				(self.old.name, self.u1.name),
				(self.new.name, self.u2.name),
				(self.mixed.name, self.u1.name),
				(self.mixed.name, self.u3.name),
			},
		)


class TestPortal(ListingCase):
	def test_bookings_list_old_new_and_mixed_invoices(self):
		documents = get_request_documents([self.u1.name, self.u2.name, self.u3.name], [fx.CUSTOMER])

		def listed(request):
			return sorted(invoice.name for invoice in documents[request]["invoices"])

		self.assertEqual(listed(self.u1.name), sorted([self.old.name, self.mixed.name]))
		self.assertEqual(listed(self.u2.name), [self.new.name])
		# An invoice billing two requests shows under both bookings
		self.assertEqual(listed(self.u3.name), [self.mixed.name])

	def test_property_vouchers_find_invoices_through_lines_and_header(self):
		vouchers = _get_vouchers("Sales Invoice", SALES_INVOICE_FIELDS, "posting_date", [fx.CUSTOMER], [], [self.u1.name])

		self.assertEqual(sorted(row.name for row in vouchers), sorted([self.old.name, self.mixed.name]))

	def test_another_customer_sees_nothing(self):
		self.assertEqual(get_request_documents([self.u1.name], ["_Test Line USR Other Customer"]), {self.u1.name: {"invoices": [], "orders": []}})


class TestPropertyBillingOverview(ListingCase):
	def test_old_new_and_mixed_lines_get_their_bill_type(self):
		for request in (self.u1, self.u2, self.u3):
			frappe.db.set_value("Utility Service Request", request.name, "utility_bill_structure", "_Test Structure")
		report = PropertyBillingOverview({"company": fx.company(), "from_date": "2027-01-01", "to_date": "2027-12-31"})
		report.bill_item_mapping = {"_Test Structure": {P1: "Rent", P2: "Rent"}}

		with patch.object(report, "update_billing_data") as update:
			report.get_invoices([P1, P2], [fx.CUSTOMER])

		# Before, the new and mixed lines had no header request, so no bill type, and were dropped
		self.assertEqual(
			sorted((call.args[0][0], call.args[1]) for call in update.call_args_list),
			[(P1, "Rent"), (P1, "Rent"), (P1, "Rent"), (P2, "Rent")],
		)


@skipUnless(has_line_column(), "needs the line field, which a migrate adds")
class TestPropertyWiseInvoicing(fx.SavepointMixin, FrappeTestCase):
	"""P2 leased from August 2026; only September invoiced, on a new invoice."""

	def setUp(self):
		super().setUp()
		fx.use_approach("Item Price")
		setup_items()
		self.request = make_request([(P2, "2026-08-01", "2026-12-31")], "2026-08-01", "2027-01-01")
		self.invoice = submitted_invoice(
			[{"item_code": P2, "rate": 2000, "base_net_amount": 2000, "utility_property": P2, "utility_service_request": self.request.name}],
			"2026-09-01",
		)

	def rows(self):
		with patch.object(property_wise_invoicing, "today", return_value="2026-11-06"):
			_columns, data = property_wise_invoicing.execute({"year": 2026, "company": fx.company(), "customer": fx.CUSTOMER})

		return [(row.get("month"), row.get("invoiced_amount")) for row in data if row.get("property") == P2]

	def test_the_invoiced_month_shows_its_amount_and_the_others_zero(self):
		rows = self.rows()

		self.assertEqual(len(rows), 4)  # August to November
		self.assertEqual(sorted(amount for _month, amount in rows), [0, 0, 0, 2000])

	def test_the_line_request_is_read(self):
		lines = property_wise_invoicing.get_invoiced_lines(
			frappe._dict(company=fx.company()), frappe.utils.getdate("2026-01-01"), frappe.utils.getdate("2026-12-31"), {P2: [P2]}
		)

		self.assertEqual([(line.item_code, line.service_request) for line in lines], [(P2, self.request.name)])
