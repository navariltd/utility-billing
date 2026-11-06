"""Tests for the rates of utility lines under Item Price, set before ERPNext's totals.

A rent line takes its request's Item Price as its price list rate before
ERPNext computes the totals, and nothing is written after that calculation, so
the totals agree with the rate on the first save and after submit. Discounts
are neither refused nor added: whatever ERPNext derives from the price list
rate is kept. A service line is prefilled with its request row's rate when it
has none, and keeps a rate the user set. A line without a property takes the
one property of its cost center.

Invoices are inserted inside the test's savepoint.
"""

import frappe

from utility_billing.utility_billing.overrides.server import sales_invoice
from utility_billing.utility_billing.tests import factories
from utility_billing.utility_billing.tests import lease_fixtures as fx
from utility_billing.utility_billing.tests.line_request_fixtures import ELECTRICITY, P1, P2, make_invoice
from utility_billing.utility_billing.tests.test_line_request import LineRequestCase
from utility_billing.utility_billing.tests.test_line_request_readers import submitted_invoice


class RatesCase(LineRequestCase):
	def insert(self, lines, posting_date="2027-03-10"):
		invoice = make_invoice(lines, posting_date, set_posting_time=1, due_date="2027-04-30")
		invoice.insert(ignore_permissions=True)
		return invoice

	def assert_consistent(self, invoice, rate, total):
		row = invoice.items[0]
		self.assertEqual((row.rate, row.amount, row.net_amount, row.base_net_amount), (rate, rate, rate, rate))
		self.assertEqual((invoice.net_total, invoice.grand_total), (total, total))
		self.assertEqual(sum(term.payment_amount for term in invoice.payment_schedule), total)


class TestRentRate(RatesCase):
	def test_the_price_list_rate_is_locked_and_a_typed_rate_left_to_erpnext(self):
		# Nothing is written after ERPNext's calculation: it keeps a typed rate,
		# and the amounts and totals agree with it on the first save
		invoice = self.insert([{"item_code": P1, "rate": 1, "price_list_rate": 1}])

		self.assertEqual(invoice.items[0].price_list_rate, 1000)
		self.assert_consistent(invoice, 1, 1)

	def test_a_line_without_a_rate_bills_the_schedule(self):
		invoice = self.insert([{"item_code": P1}])

		self.assertEqual(invoice.items[0].price_list_rate, 1000)
		self.assert_consistent(invoice, 1000, 1000)

	def test_erpnext_derived_rate_is_not_overwritten_through_submit(self):
		invoice = self.insert([{"item_code": P1, "price_list_rate": 1000, "discount_percentage": 10}])
		self.assertEqual(invoice.items[0].price_list_rate, 1000)
		self.assert_consistent(invoice, 900, 900)

		invoice.submit()

		self.assert_consistent(invoice, 900, 900)
		debit = frappe.db.sql("select sum(debit) from `tabGL Entry` where voucher_no=%s and is_cancelled=0", invoice.name)[0][0]
		self.assertEqual(debit, 900)

	def test_erpnext_derived_rate_from_a_discount_amount_is_not_overwritten(self):
		invoice = self.insert([{"item_code": P1, "price_list_rate": 1000, "discount_amount": 100}])

		self.assert_consistent(invoice, 900, 900)

	def test_a_price_list_rate_off_the_schedule_is_refused(self):
		invoice = make_invoice([{"item_code": P1, "price_list_rate": 1, "rate": 1}], "2027-03-10")

		with self.assertRaisesRegex(frappe.ValidationError, "price list rate of .* must be"):
			sales_invoice.govern_utility_lines(invoice)


class TestServiceRate(RatesCase):
	def test_a_line_without_a_rate_takes_the_request_rate(self):
		invoice = self.insert([{"item_code": ELECTRICITY, "utility_property": P1}])

		self.assert_consistent(invoice, 200, 200)

	def test_a_rate_set_by_the_user_is_kept(self):
		invoice = self.insert([{"item_code": ELECTRICITY, "utility_property": P1, "rate": 250, "price_list_rate": 250}])

		self.assert_consistent(invoice, 250, 250)
		self.assertEqual(invoice.items[0].utility_service_request, self.u1.name)

	def test_a_service_rate_derived_by_erpnext_is_not_overwritten(self):
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

	def test_the_cost_center_gives_the_property_when_only_one_has_it(self):
		invoice = self.insert([{"item_code": ELECTRICITY, "cost_center": self.center_2}])

		self.assertEqual(
			(invoice.items[0].utility_property, invoice.items[0].utility_service_request, invoice.items[0].rate),
			(P2, self.u3.name, 250),
		)

	def test_a_cost_center_shared_by_two_properties_gives_none(self):
		frappe.db.set_value("Utility Property", P2, "cost_center", self.center_1)

		with self.assertRaisesRegex(frappe.ValidationError, "Pick the property on this line"):
			self.insert([{"item_code": ELECTRICITY, "cost_center": self.center_1}])

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
