"""Tests for the rates of utility lines under Item Price, set before ERPNext's totals.

A rent line takes its request's Item Price as its price list rate before
ERPNext computes the totals, and nothing is written after that calculation, so
the totals agree with the rate on the first save and after submit. Rent is
locked: a rate ERPNext keeps that is not the price (typed, discounted, with a
margin or from a pricing rule) is refused, never overwritten. A service line is prefilled with its request row's rate when it
has none, and keeps a rate the user set. A line without a property takes the
one property of its cost center.

Invoices are inserted inside the test's savepoint.
"""

import csv
import os
import tempfile

import frappe
from frappe.core.doctype.data_import.importer import Importer

from utility_billing.api.sales_invoice import get_line_rate
from utility_billing.utility_billing.overrides.server import sales_invoice
from utility_billing.utility_billing.tests import factories
from utility_billing.utility_billing.tests import lease_fixtures as fx
from utility_billing.utility_billing.tests.line_request_fixtures import ELECTRICITY, P1, P2, currency, make_invoice
from utility_billing.utility_billing.tests.test_line_request import LineRequestCase
from utility_billing.utility_billing.tests.test_line_request_readers import submitted_invoice


def import_rows(header, row):
	"""Insert one Sales Invoice through Data Import's own importer, without its commits."""
	path = os.path.join(tempfile.mkdtemp(), "invoices.csv")
	with open(path, "w", newline="") as handle:
		csv.writer(handle).writerows([header, row])

	data_import = frappe.get_doc(doctype="Data Import", reference_doctype="Sales Invoice", import_type="Insert New Records")
	data_import.db_set = lambda *args, **kwargs: None
	importer = Importer("Sales Invoice", data_import=data_import, file_path=path, console=True)
	importer.before_import()
	try:
		return importer.process_doc(importer.import_file.get_payloads_for_import()[0].doc)[0]
	finally:
		frappe.flags.in_import = False
		os.remove(path)


class RatesCase(LineRequestCase):
	def insert(self, lines, posting_date="2027-03-10", due_date="2027-04-30"):
		invoice = make_invoice(lines, posting_date, set_posting_time=1, due_date=due_date)
		invoice.insert(ignore_permissions=True)
		return invoice

	def assert_consistent(self, invoice, rate, total):
		row = invoice.items[0]
		self.assertEqual((row.rate, row.amount, row.net_amount, row.base_net_amount), (rate, rate, rate, rate))
		self.assertEqual((invoice.net_total, invoice.grand_total), (total, total))
		self.assertEqual(sum(term.payment_amount for term in invoice.payment_schedule), total)


class TestRentRate(RatesCase):
	def save_with(self, **changes):
		invoice = self.insert([{"item_code": P1}])
		invoice.items[0].update(changes)
		invoice.save(ignore_permissions=True)
		return invoice

	def test_a_line_without_a_rate_bills_the_schedule(self):
		invoice = self.insert([{"item_code": P1}])

		self.assertEqual(invoice.items[0].price_list_rate, 1000)
		self.assert_consistent(invoice, 1000, 1000)

	def test_the_schedule_rate_stays_consistent_through_submit(self):
		invoice = self.insert([{"item_code": P1}])

		invoice.submit()

		self.assert_consistent(invoice, 1000, 1000)
		debit = frappe.db.sql("select sum(debit) from `tabGL Entry` where voucher_no=%s and is_cancelled=0", invoice.name)[0][0]
		self.assertEqual(debit, 1000)

	def test_a_typed_rate_is_refused(self):
		with self.assertRaisesRegex(frappe.ValidationError, "Row #1: .*is rent and bills .*1,000.00.* not .*800.00"):
			self.insert([{"item_code": P1, "rate": 800}])

	def test_a_rate_edited_on_a_draft_is_refused(self):
		# The form sends the discount ERPNext derives from it
		with self.assertRaisesRegex(frappe.ValidationError, "is rent and bills"):
			self.save_with(rate=800, discount_amount=200)
		with self.assertRaisesRegex(frappe.ValidationError, "is rent and bills"):
			self.save_with(rate=1200, margin_type="Amount", margin_rate_or_amount=200)

	def test_a_discount_or_margin_is_refused(self):
		for line in (
			{"discount_percentage": 10},
			{"discount_amount": 100},
			{"margin_type": "Percentage", "margin_rate_or_amount": 10},
		):
			with self.subTest(**line), self.assertRaisesRegex(frappe.ValidationError, "Remove the discount, margin or pricing rule"):
				self.insert([{"item_code": P1, "price_list_rate": 1000, **line}])

	def test_a_price_list_rate_edited_with_its_rate_is_refused(self):
		with self.assertRaisesRegex(frappe.ValidationError, "is rent and bills"):
			self.save_with(price_list_rate=800, rate=800)

	def test_a_price_list_rate_edited_alone_is_set_back(self):
		# Before ERPNext's calculation, as before: nothing billed differs
		invoice = self.save_with(price_list_rate=800)

		self.assertEqual(invoice.items[0].price_list_rate, 1000)
		self.assert_consistent(invoice, 1000, 1000)

	def test_a_pricing_rule_on_rent_is_refused(self):
		frappe.get_doc(
			{
				"doctype": "Pricing Rule",
				"title": "_Test Line Rate Rent Discount",
				"apply_on": "Item Code",
				"items": [{"item_code": P1}],
				"selling": 1,
				"applicable_for": "Customer",
				"customer": fx.CUSTOMER,
				"company": fx.company(),
				"rate_or_discount": "Discount Percentage",
				"discount_percentage": 10,
				"currency": currency(),
			}
		).insert(ignore_permissions=True)

		with self.assertRaisesRegex(frappe.ValidationError, "is rent and bills"):
			self.insert([{"item_code": P1}])

	def test_a_data_import_rate_is_refused(self):
		header = ["Customer", "Company", "Posting Date", "Set Posting Time", "Due Date", "Currency", "Price List", "Item (Items)", "Quantity (Items)", "UOM (Items)", "UOM Conversion Factor (Items)", "Rate (Items)"]
		row = [fx.CUSTOMER, fx.company(), "2027-03-10", 1, "2027-04-30", currency(), fx.PRICE_LIST, P1, 1, "Nos", 1, 800]

		with self.assertRaisesRegex(frappe.ValidationError, "is rent and bills"):
			import_rows(header, row)

	def test_a_price_list_rate_off_the_schedule_is_refused(self):
		invoice = make_invoice([{"item_code": P1, "price_list_rate": 1, "rate": 1}], "2027-03-10")

		with self.assertRaisesRegex(frappe.ValidationError, "price list rate of .* must be"):
			sales_invoice.govern_utility_lines(invoice)


class TestRentRateUnderAutoRepeat(RatesCase):
	def test_a_discounted_rent_line_is_kept(self):
		fx.use_approach("Auto Repeat")

		invoice = self.insert([{"item_code": P1, "price_list_rate": 1000, "discount_percentage": 10}])

		self.assert_consistent(invoice, 900, 900)


class TestAutoRepeatCopyRate(RatesCase):
	def copy(self, reference, posting_date, header=None):
		"""As Auto Repeat makes a draft: copy, new dates, ``on_recurring``, insert."""
		draft = frappe.copy_doc(reference)
		draft.update({"posting_date": posting_date, "due_date": posting_date, "set_posting_time": 1, "auto_repeat": header and "_Test AR"})
		draft.set("payment_schedule", [])
		draft.on_recurring(reference_doc=reference, auto_repeat_doc=frappe._dict())
		return draft

	def test_a_copy_bills_the_price_of_its_new_date(self):
		june = self.insert([{"item_code": P1}], "2027-06-10", due_date="2027-06-30")

		draft = self.copy(june, "2027-07-10")
		draft.insert(ignore_permissions=True)

		self.assertEqual((draft.items[0].utility_service_request, draft.items[0].price_list_rate), (self.u2.name, 1200))
		self.assert_consistent(draft, 1200, 1200)

	def test_a_service_line_of_a_copy_keeps_its_rate(self):
		march = self.insert([{"item_code": ELECTRICITY, "utility_property": P1, "rate": 260, "price_list_rate": 260}])

		draft = self.copy(march, "2027-04-10")

		self.assertEqual(draft.items[0].rate, 260)

	def test_a_copy_keeping_its_header_is_left_as_it_is(self):
		reference = make_invoice([{"item_code": P1, "rate": 1000, "price_list_rate": 1000}], "2027-06-10", header=self.u1.name)

		draft = self.copy(reference, "2027-07-10", header=True)

		self.assertEqual((draft.items[0].price_list_rate, draft.items[0].rate), (1000, 1000))


class TestServiceRate(RatesCase):
	def test_a_line_without_a_rate_takes_the_request_rate(self):
		invoice = self.insert([{"item_code": ELECTRICITY, "utility_property": P1}])

		self.assert_consistent(invoice, 200, 200)

	def test_a_rate_set_by_the_user_is_kept(self):
		invoice = self.insert([{"item_code": ELECTRICITY, "utility_property": P1, "rate": 250, "price_list_rate": 250}])

		self.assert_consistent(invoice, 250, 250)
		self.assertEqual(invoice.items[0].utility_service_request, self.u1.name)

	def test_a_service_rate_derived_by_erpnext_is_not_overwritten(self):
		# Discounts stay allowed on service lines
		invoice = self.insert([{"item_code": ELECTRICITY, "utility_property": P1, "price_list_rate": 200, "discount_percentage": 10}])

		self.assert_consistent(invoice, 180, 180)

	def test_an_edited_rate_still_counts_for_the_duplicate_month(self):
		old = submitted_invoice([{"item_code": ELECTRICITY, "rate": 200}], "2027-03-01", header=self.u1.name)

		with self.assertRaisesRegex(frappe.ValidationError, old.name):
			self.insert([{"item_code": ELECTRICITY, "utility_property": P1, "rate": 250, "price_list_rate": 250}], "2027-03-20")


class TestPropertyAndCostCenter(RatesCase):
	def setUp(self):
		super().setUp()
		company = fx.company()
		self.center_1 = factories.ensure_cost_center("_Test Line Rate Center 1", company)
		self.center_2 = factories.ensure_cost_center("_Test Line Rate Center 2", company)
		self.center_hand = factories.ensure_cost_center("_Test Line Rate Center Hand", company)
		frappe.db.set_value("Utility Property", P1, "cost_center", self.center_1)
		frappe.db.set_value("Utility Property", P2, "cost_center", self.center_2)
		frappe.db.sql(
			"update `tabUtility Service Request Item` set cost_center=null where parent in %s",
			[(self.u1.name, self.u3.name)],
		)

	def test_a_cost_center_used_by_one_property_never_gives_the_property(self):
		invoice = self.insert([{"item_code": ELECTRICITY, "cost_center": self.center_2, "rate": 210}])

		row = invoice.items[0]
		self.assertEqual(
			(row.get("utility_property"), row.get("utility_service_request"), row.cost_center, row.rate),
			(None, None, self.center_2, 210),
		)

	def test_a_cost_center_shared_by_two_properties_gives_none(self):
		frappe.db.set_value("Utility Property", P2, "cost_center", self.center_1)

		invoice = self.insert([{"item_code": ELECTRICITY, "cost_center": self.center_1, "rate": 210}])

		row = invoice.items[0]
		self.assertEqual(
			(row.get("utility_property"), row.get("utility_service_request"), row.cost_center, row.rate),
			(None, None, self.center_1, 210),
		)

	def test_the_property_gives_the_cost_center(self):
		invoice = self.insert([{"item_code": ELECTRICITY, "utility_property": P2}])

		self.assertEqual(invoice.items[0].cost_center, self.center_2)

	def test_a_cost_center_set_by_hand_is_kept(self):
		invoice = self.insert([{"item_code": ELECTRICITY, "utility_property": P2, "cost_center": self.center_hand}])

		self.assertEqual(invoice.items[0].cost_center, self.center_hand)

	def test_a_cost_center_already_on_the_line_is_kept_even_from_another_property(self):
		# Why the form no longer copies row 1's cost center: the server cannot tell a
		# copied one from one set by hand, and keeps it over the picked property's
		invoice = self.insert([{"item_code": ELECTRICITY, "utility_property": P2, "cost_center": self.center_1}])

		self.assertEqual((invoice.items[0].utility_property, invoice.items[0].cost_center), (P2, self.center_1))

	def test_a_line_left_blank_gets_the_picked_property_cost_center(self):
		invoice = self.insert([{"item_code": ELECTRICITY, "utility_property": P2, "cost_center": None}])

		self.assertEqual(invoice.items[0].cost_center, self.center_2)

	def test_a_utility_line_without_a_cost_center_is_refused(self):
		entry = frappe._dict(row=frappe._dict(idx=1, item_code=ELECTRICITY, cost_center=None))

		with self.assertRaisesRegex(frappe.ValidationError, "needs a cost center"):
			sales_invoice.check_utility_cost_centers(frappe._dict(), [entry])


class TestFormPrice(RatesCase):
	def test_a_converted_price_comes_back_rounded_as_the_line_stores_it(self):
		# 1000 x 1.37 is 1370.0000000000002 in floats: the form took that noise for
		# another price and set it on a saved draft, which then lost its Submit button
		rate = get_line_rate(
			item_code=P1,
			posting_date="2027-03-10",
			customer=fx.CUSTOMER,
			price_list=fx.PRICE_LIST,
			uom="Nos",
			qty=1,
			conversion_factor=1,
			plc_conversion_rate=1.37,
			conversion_rate=1,
			utility_service_request=self.u1.name,
		)

		self.assertEqual(repr(rate), "1370.0")

	def test_no_price_is_still_none(self):
		self.assertIsNone(get_line_rate(item_code=P1, posting_date="2026-01-10", customer=fx.CUSTOMER, price_list=fx.PRICE_LIST, utility_service_request=self.u1.name))


class TestServiceLineWithoutProperty(RatesCase):
	def test_it_saves_as_an_ordinary_line(self):
		company_center = frappe.get_cached_value("Company", fx.company(), "cost_center")

		invoice = self.insert([{"item_code": ELECTRICITY, "rate": 210}])

		row = invoice.items[0]
		self.assertEqual(
			(row.get("utility_property"), row.get("utility_service_request"), row.cost_center, row.rate),
			(None, None, company_center, 210),
		)
		self.assert_consistent(invoice, 210, 210)

	def test_with_a_property_it_still_finds_its_request(self):
		invoice = self.insert([{"item_code": ELECTRICITY, "utility_property": P1}])

		self.assertEqual((invoice.items[0].utility_service_request, invoice.items[0].rate), (self.u1.name, 200))

	def test_a_rent_line_on_the_same_invoice_is_still_locked(self):
		with self.assertRaisesRegex(frappe.ValidationError, "is rent and bills"):
			self.insert([{"item_code": ELECTRICITY, "rate": 210}, {"item_code": P1, "rate": 800}])


class TestServiceLineRules(RatesCase):
	"""The agreed rules for service lines (1 to 6) and rent lines (7), on saved invoices.

	P1 is leased by U1 (listing Electricity at 200) to June 2027, then by U2
	(no Electricity); P2 by U3 (Electricity at 250) all 2027.
	"""

	def setUp(self):
		super().setUp()
		company = fx.company()
		self.company_center = frappe.get_cached_value("Company", company, "cost_center")
		self.center_1 = factories.ensure_cost_center("_Test Line Rule Center 1", company)
		self.center_2 = factories.ensure_cost_center("_Test Line Rule Center 2", company)
		self.center_hand = factories.ensure_cost_center("_Test Line Rule Center Hand", company)
		frappe.db.set_value("Utility Property", P1, "cost_center", self.center_1)
		frappe.db.set_value("Utility Property", P2, "cost_center", self.center_2)
		frappe.db.sql(
			"update `tabUtility Service Request Item` set cost_center=null where parent in %s",
			[(self.u1.name, self.u3.name)],
		)

	def line(self, invoice):
		row = invoice.items[0]
		return (row.get("utility_property"), row.get("utility_service_request"), row.cost_center, row.rate)

	def test_rule_1_a_cost_center_is_kept_and_gives_no_property(self):
		invoice = self.insert([{"item_code": ELECTRICITY, "cost_center": self.center_2, "rate": 210}])

		self.assertEqual(self.line(invoice), (None, None, self.center_2, 210))

	def test_rule_2_the_property_gives_its_cost_center_unless_one_was_set_by_hand(self):
		filled = self.insert([{"item_code": ELECTRICITY, "utility_property": P2}])
		by_hand = self.insert([{"item_code": ELECTRICITY, "utility_property": P2, "cost_center": self.center_hand}])
		# Also for a property no request covers on the date
		unlinked = self.insert([{"item_code": ELECTRICITY, "utility_property": P1, "rate": 90}], "2027-09-10", due_date="2027-09-30")

		self.assertEqual(filled.items[0].cost_center, self.center_2)
		self.assertEqual(by_hand.items[0].cost_center, self.center_hand)
		self.assertEqual(unlinked.items[0].cost_center, self.center_1)

	def test_rule_3_a_covered_property_links_its_request_and_prefills_only_a_missing_rate(self):
		prefilled = self.insert([{"item_code": ELECTRICITY, "utility_property": P1}])
		typed = self.insert([{"item_code": ELECTRICITY, "utility_property": P1, "rate": 260}])

		self.assertEqual(self.line(prefilled), (P1, self.u1.name, self.center_1, 200))
		self.assertEqual(self.line(typed), (P1, self.u1.name, self.center_1, 260))

	def test_rule_4_a_property_no_request_covers_is_kept_without_a_request(self):
		invoice = self.insert([{"item_code": ELECTRICITY, "utility_property": P1, "rate": 90}], "2027-09-10", due_date="2027-09-30")

		self.assertEqual(self.line(invoice), (P1, None, self.center_1, 90))

	def test_rule_5_a_blank_property_is_an_ordinary_line(self):
		invoice = self.insert([{"item_code": ELECTRICITY, "rate": 75}])

		self.assertEqual(self.line(invoice), (None, None, self.company_center, 75))

	def test_rule_6_a_typed_rate_or_discount_survives_a_new_property_or_date(self):
		invoice = self.insert([{"item_code": ELECTRICITY, "utility_property": P1, "rate": 260}])
		discounted = self.insert([{"item_code": ELECTRICITY, "utility_property": P1, "price_list_rate": 200, "discount_percentage": 10}])

		invoice.items[0].utility_property = P2
		invoice.items[0].custom_posting_date = "2027-04-01"
		invoice.save(ignore_permissions=True)
		discounted.items[0].utility_property = P2
		discounted.save(ignore_permissions=True)

		self.assertEqual(self.line(invoice), (P2, self.u3.name, self.center_1, 260))
		self.assertEqual((discounted.items[0].discount_percentage, discounted.items[0].rate), (10, 180))
		self.assert_consistent(discounted, 180, 180)

	def test_rule_7_rent_stays_strict(self):
		with self.assertRaisesRegex(frappe.ValidationError, "is rent and bills"):
			self.insert([{"item_code": P1, "rate": 800}])

		# A rent item shared by several properties still asks for the property
		frappe.db.set_value("Utility Property", P2, "service_item", P1)
		with self.assertRaisesRegex(frappe.ValidationError, "Pick the property on this line"):
			self.insert([{"item_code": P1}])
