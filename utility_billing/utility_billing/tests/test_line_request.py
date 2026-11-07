"""Tests for the Utility Service Request of each Sales Invoice line, under Item Price.

Covers the resolution rules of ``line_request``: by property and date, a
service line without a property left ordinary, the user's pick between
several, and the blocks; the header of a draft moved onto its lines; and the API the form uses.
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
from utility_billing.utility_billing.utils.line_request import resolve_lines
from utility_billing.utility_billing.tests.line_request_fixtures import (
	billed,
	ELECTRICITY,
	OTHER_CUSTOMER,
	OTHER_ITEM,
	P1,
	P2,
	make_invoice,
	make_price,
	make_request,
	prefill,
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
		# As a save runs them: the rates and ERPNext's totals, then the checks
		prefill(invoice)
		return sales_invoice.govern_utility_lines(invoice)

	def requests(self, invoice):
		return [row.get("utility_service_request") for row in invoice.items]


class TestByProperty(LineRequestCase):
	def test_two_requests_for_one_property_in_different_periods(self):
		march = make_invoice([{"item_code": P1}], "2027-03-10")
		september = make_invoice([{"item_code": P1}], "2027-09-10")

		self.govern(march)
		self.govern(september)

		self.assertEqual((self.requests(march), march.items[0].price_list_rate), ([self.u1.name], 1000))
		self.assertEqual((self.requests(september), september.items[0].price_list_rate), ([self.u2.name], 1200))
		self.assertIsNone(march.utility_service_request)

	def test_one_invoice_bills_a_property_across_both_requests(self):
		invoice = make_invoice(
			[{"item_code": P1, "custom_posting_date": "2027-06-01"}, {"item_code": P1, "custom_posting_date": "2027-07-01"}],
			"2027-06-01",
		)

		self.govern(invoice)

		self.assertEqual(self.requests(invoice), [self.u1.name, self.u2.name])
		self.assertEqual([billed(row) for row in invoice.items], [1000, 1200])

	def test_an_invoice_with_two_properties_from_two_requests(self):
		invoice = make_invoice([{"item_code": P1}, {"item_code": P2}], "2027-03-10")

		governed = self.govern(invoice)

		self.assertEqual(self.requests(invoice), [self.u1.name, self.u3.name])
		self.assertEqual([row.utility_property for row in invoice.items], [P1, P2])
		self.assertEqual([billed(row) for row in invoice.items], [1000, 2000])
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

	def test_electricity_without_a_property_is_an_ordinary_line(self):
		invoice = make_invoice([{"item_code": ELECTRICITY, "rate": 180}], "2027-03-10")

		self.assertEqual(self.govern(invoice), [])

		self.assertEqual(self.requests(invoice), [None])
		self.assertEqual((invoice.items[0].get("utility_property"), invoice.items[0].rate), (None, 180))

	def test_a_property_not_leased_on_the_date_is_blocked(self):
		invoice = make_invoice([{"item_code": P2}], "2028-02-10")

		with self.assertRaisesRegex(frappe.ValidationError, "No Utility Service Request of .* leases"):
			self.govern(invoice)

	def test_the_rate_never_chooses_the_request(self):
		# 1200 is U2's price; March is U1's lease, so the line is held to U1's price
		invoice = make_invoice([{"item_code": P1, "rate": 1200, "price_list_rate": 1200}], "2027-03-10")

		with self.assertRaisesRegex(frappe.ValidationError, f"bills .*1,000.00.*{self.u1.name}"):
			self.govern(invoice)

		self.assertEqual((self.requests(invoice), invoice.items[0].price_list_rate), ([self.u1.name], 1000))

	def test_a_request_set_by_hand_on_a_derived_line_is_replaced(self):
		invoice = make_invoice([{"item_code": P1, "utility_service_request": self.u2.name}], "2027-03-10")

		self.govern(invoice)

		self.assertEqual(self.requests(invoice), [self.u1.name])


class TestTwoPropertiesListingOneItem(LineRequestCase):
	"""Electricity on two properties' requests, as for customer Omondi: the property decides."""

	def resolve(self, posting_date, **line):
		invoice = make_invoice([{"item_code": ELECTRICITY, **line}], posting_date)
		return next(iter(resolve_lines(invoice, invoice.items).values()))

	def test_each_property_gets_its_own_request(self):
		self.assertEqual(self.resolve("2027-03-10", utility_property=P1).service_request, self.u1.name)
		self.assertEqual(self.resolve("2027-03-10", utility_property=P2).service_request, self.u3.name)

	def test_without_a_property_the_line_is_ordinary_and_says_nothing(self):
		result = self.resolve("2027-03-10")

		self.assertEqual((result.status, result.service_request, result.message, result.candidates), ("ordinary", None, None, []))

	def test_the_lease_message_stays_apart_from_the_missing_property_one(self):
		result = self.resolve("2027-09-10", utility_property=P1)

		self.assertNotIn("has no property", result.message)
		self.assertIn("No Utility Service Request of", result.message)

	def test_a_property_not_billing_the_item_on_the_date_names_the_one_that_does(self):
		# P1 is leased by U2 in September, but U2 does not list Electricity
		result = self.resolve("2027-09-10", utility_property=P1)

		self.assertEqual((result.status, result.property_candidates), ("not_covered", [P2]))
		self.assertIn(f"can be billed for: <strong>{P2}</strong>", result.message)

	def test_a_date_no_property_covers_says_so(self):
		result = self.resolve("2028-03-10", utility_property=P2)

		self.assertIn("No property of", result.message)


class TestLineFieldVisible(FrappeTestCase):
	def test_the_line_request_is_never_read_only(self):
		import json
		import os

		path = os.path.join(os.path.dirname(__file__), "..", "custom", "sales_invoice_item.json")
		fields = {field["fieldname"]: field for field in json.load(open(path))["custom_fields"]}

		# Frappe hides an empty read only field, so the user could not see or pick it
		self.assertFalse(fields["utility_service_request"]["read_only"])
		self.assertFalse(fields["utility_service_request"]["read_only_depends_on"])


class TestOtherLines(LineRequestCase):
	"""Lines billing no utility item, and meter lines."""

	def test_an_ordinary_line_loses_a_copied_property(self):
		invoice = make_invoice([{"item_code": P1}, {"item_code": OTHER_ITEM, "rate": 5, "utility_property": P1}], "2027-03-10")

		self.govern(invoice)

		self.assertEqual([row.get("utility_property") for row in invoice.items], [P1, None])

	def test_a_meter_line_keeps_its_property(self):
		invoice = make_invoice(
			[{"item_code": ELECTRICITY, "rate": 37, "meter_reading": "_Test MR", "utility_property": P1}], "2027-03-10"
		)

		self.govern(invoice)

		self.assertEqual(invoice.items[0].utility_property, P1)

	def test_a_draft_keeping_its_header_keeps_an_ordinary_property(self):
		invoice = make_invoice(
			[{"item_code": P1}, {"item_code": OTHER_ITEM, "rate": 5, "utility_property": P1}],
			"2027-03-10",
			header=self.u1.name,
			auto_repeat="_Test AR",
		)

		self.govern(invoice)

		self.assertEqual(invoice.items[1].utility_property, P1)

	def test_auto_repeat_sites_keep_every_property(self):
		fx.use_approach("Auto Repeat")
		invoice = make_invoice([{"item_code": OTHER_ITEM, "rate": 5, "utility_property": P1}], "2027-03-10")

		sales_invoice.validate(invoice)

		self.assertEqual(invoice.items[0].utility_property, P1)


class TestErpnextRowCopies(fx.SavepointMixin, FrappeTestCase):
	"""Guard: the form filters ERPNext's row copies of the property and the cost center at
	their two entry points, so a change to any of them must fail here."""

	def source(self, app, path):
		with open(frappe.get_app_path(app, *path.split("/"))) as handle:
			return handle.read()

	def test_the_first_row_copy_entry_point_still_exists(self):
		source = self.source("frappe", "public/js/frappe/form/script_manager.js")

		self.assertIn("copy_from_first_row(parentfield, current_row, fieldnames) {", source)

	def test_the_sales_invoice_still_copies_the_cost_center_through_it(self):
		source = self.source("erpnext", "accounts/doctype/sales_invoice/sales_invoice.js")

		self.assertIn("items_add(doc, cdt, cdn) {", source)
		self.assertIn('const field_copy = ["income_account", "discount_account", "cost_center"];', source)
		self.assertIn('this.frm.script_manager.copy_from_first_row("items", row, field_copy);', source)

	def test_the_dimension_copy_still_goes_through_it_on_a_new_row(self):
		dimensions = self.source("erpnext", "public/js/utils/dimension_tree_filter.js")
		transaction = self.source("erpnext", "public/js/controllers/transaction.js")

		self.assertIn('frm.script_manager.copy_from_first_row(fieldname, row, [dimension["fieldname"]]);', dimensions)
		self.assertIn('erpnext.accounts.dimensions.copy_dimension_from_first_row(frm, cdt, cdn, "items")', transaction)

	def test_the_row_to_row_copy_entry_point_still_exists_and_is_used(self):
		utils = self.source("erpnext", "public/js/utils.js")
		transaction = self.source("erpnext", "public/js/controllers/transaction.js")

		self.assertIn("copy_value_in_all_rows: function (doc, dt, dn, table_fieldname, fieldname) {", utils)
		self.assertIn('erpnext.utils.copy_value_in_all_rows(doc, cdt, cdn, "items", "cost_center");', transaction)
		self.assertIn('erpnext.utils.copy_value_in_all_rows(doc, cdt, cdn, "items", dim);', transaction)

	def test_the_cost_center_and_the_property_are_still_copied_dimensions(self):
		from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import get_dimensions

		fieldnames = [dimension.fieldname for dimension in get_dimensions(True)[0]]
		self.assertIn("cost_center", fieldnames)
		self.assertIn("utility_property", fieldnames)

	def test_a_new_row_still_starts_with_the_company_cost_center(self):
		self.assertEqual(frappe.get_meta("Sales Invoice Item").get_field("cost_center").default, ":Company")

	def test_a_row_cost_center_still_beats_the_company_default(self):
		"""Why the copies are filtered: ERPNext keeps a row's cost center over the company's."""
		from erpnext.stock.get_item_details import get_default_cost_center

		from utility_billing.utility_billing.tests import factories

		company = frappe.db.get_value("Company", {}, "name")
		other = factories.ensure_cost_center("_Test Copied Row Center", company)
		ctx = frappe._dict(company=company, customer="_Test", item_code=None)

		# A blank row falls back to the company's; a row carrying one keeps it
		self.assertNotEqual(get_default_cost_center(ctx, company=company), other)
		self.assertEqual(get_default_cost_center(frappe._dict(ctx, cost_center=other), company=company), other)


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
	"""Requests of another customer listing Electricity without any property: a line without a property stays ordinary."""

	def setUp(self):
		super().setUp()
		fx.use_approach("Item Price")
		setup_items()
		self.n1 = make_request([], "2027-01-01", "2027-07-01", [(ELECTRICITY, 200)], customer=OTHER_CUSTOMER)
		self.n2 = make_request([], "2027-07-01", "2028-01-01", [(ELECTRICITY, 300)], customer=OTHER_CUSTOMER)

	def invoice(self, posting_date, rate=200, **line):
		return make_invoice([{"item_code": ELECTRICITY, "rate": rate, **line}], posting_date, customer=OTHER_CUSTOMER)

	def test_a_line_without_a_property_takes_no_request(self):
		invoice = self.invoice("2027-03-10", rate=210)

		self.assertEqual(sales_invoice.govern_utility_lines(invoice), [])

		self.assertEqual((invoice.items[0].get("utility_service_request"), invoice.items[0].rate), (None, 210))

	def test_a_request_picked_on_it_is_cleared(self):
		invoice = self.invoice("2027-03-10", utility_service_request=self.n2.name)

		sales_invoice.govern_utility_lines(invoice)

		self.assertIsNone(invoice.items[0].get("utility_service_request"))

	def test_no_date_is_refused(self):
		invoice = self.invoice("2029-03-10")

		sales_invoice.govern_utility_lines(invoice)

		self.assertIsNone(invoice.items[0].get("utility_service_request"))


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
		self.assertEqual([billed(row) for row in invoice.items], [1000, 200, 5])

	def test_a_header_with_several_properties_leaves_the_line_ordinary(self):
		both = make_request(
			[(P1, "2028-01-01", "2028-12-31"), (P2, "2028-01-01", "2028-12-31")],
			"2028-01-01",
			"2029-01-01",
			[(ELECTRICITY, 300)],
		)
		invoice = make_invoice([{"item_code": ELECTRICITY, "rate": 300}], "2028-03-10", header=both.name)

		self.govern(invoice)

		self.assertIsNone(invoice.utility_service_request)
		self.assertEqual((self.requests(invoice), invoice.items[0].get("utility_property")), ([None], None))

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
		self.assertEqual((second.status, second.service_request, second.message), ("ordinary", None, None))

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
		self.assertEqual([billed(row) for row in invoice.items], [1000, 200])


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
