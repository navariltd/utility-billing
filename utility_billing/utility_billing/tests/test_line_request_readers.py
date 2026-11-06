"""Tests for the readers of an invoice's Utility Service Request, under Item Price.

Every reader takes a line's own request, else the invoice header's, so old
invoices (header only), new ones (lines only) and both mixed are read alike.
Drafts are unsaved and governed through the hook functions. Submitted invoices
read by queries are written straight to the database inside the savepoint;
those carrying a request on their lines need the line field's column, which a
migrate adds, so their tests are skipped before it.
"""

from contextlib import contextmanager
from unittest import skipUnless
from unittest.mock import patch

import frappe
from frappe.model.document import Document
from frappe.utils import add_days, today

from utility_billing.api.sales_invoice import get_line_rate
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
)
from utility_billing.utility_billing.tests.test_line_request import LineRequestCase, has_line_column
from utility_billing.utility_billing.utils import auto_repeat
from utility_billing.utility_billing.utils.line_request import line_requests_stored

needs_column = skipUnless(has_line_column(), "needs the line field, which a migrate adds")


def submitted_invoice(lines, posting_date, header=None, **values):
	"""Write a submitted invoice straight to the database, without validation."""
	invoice = make_invoice(lines, posting_date, header=header, **values)
	invoice.name = f"_Test Line USR {frappe.generate_hash(length=8)}"
	invoice.docstatus = 1
	invoice.db_insert()
	for row in invoice.items:
		row.update(
			{
				"name": frappe.generate_hash(length=10),
				"parent": invoice.name,
				"parenttype": "Sales Invoice",
				"parentfield": "items",
				"docstatus": 1,
				"custom_posting_date": row.get("custom_posting_date") or posting_date,
			}
		)
		row.db_insert()

	return invoice


@contextmanager
def captured_inserts(doctype):
	"""Yield the documents of ``doctype`` inserted inside the block, as they were inserted."""
	inserted = []
	insert = Document.insert

	def capture(self, *args, **kwargs):
		if self.doctype == doctype:
			inserted.append(self)
		return insert(self, *args, **kwargs)

	with patch.object(Document, "insert", capture):
		yield inserted


class TestRateLock(LineRequestCase):
	def test_a_new_line_takes_the_price_of_its_own_request(self):
		invoice = make_invoice([{"item_code": P1, "rate": 1000, "price_list_rate": 1000}], "2027-09-10")

		self.govern(invoice)

		self.assertEqual((invoice.items[0].utility_service_request, invoice.items[0].rate), (self.u2.name, 1200))

	def test_mixed_lines_each_take_their_request_price(self):
		invoice = make_invoice(
			[
				{"item_code": P1, "custom_posting_date": "2027-05-01"},
				{"item_code": P1, "custom_posting_date": "2027-08-01"},
				{"item_code": P2},
			],
			"2027-05-01",
		)

		self.govern(invoice)

		self.assertEqual([row.rate for row in invoice.items], [1000, 1200, 2000])

	def test_the_form_rate_uses_the_line_request(self):
		args = {"customer": fx.CUSTOMER, "price_list": fx.PRICE_LIST, "uom": "Nos", "qty": 1}

		self.assertEqual(get_line_rate(P1, "2027-09-10", utility_service_request=self.u2.name, **args), 1200)
		# U1's prices end with its lease
		self.assertIsNone(get_line_rate(P1, "2027-09-10", utility_service_request=self.u1.name, **args))

	def test_a_secondary_rate_is_checked_against_its_line_request(self):
		invoice = make_invoice([{"item_code": ELECTRICITY, "utility_property": P2, "rate": 200}], "2027-03-10")

		with self.assertRaisesRegex(frappe.ValidationError, f"250.* agreed on Utility Service Request <strong>{self.u3.name}"):
			self.govern(invoice)


class TestDuplicateMonth(LineRequestCase):
	def test_an_old_invoice_blocks_the_same_month_of_its_request(self):
		old = submitted_invoice([{"item_code": ELECTRICITY, "rate": 200}], "2027-03-01", header=self.u1.name)
		draft = make_invoice([{"item_code": ELECTRICITY, "utility_property": P1, "rate": 200}], "2027-03-20")

		with self.assertRaisesRegex(frappe.ValidationError, f"already invoiced for March 2027 on <strong>{old.name}"):
			self.govern(draft)

	def test_an_old_invoice_of_another_request_does_not_block(self):
		submitted_invoice([{"item_code": ELECTRICITY, "rate": 200}], "2027-03-01", header=self.u1.name)
		draft = make_invoice([{"item_code": ELECTRICITY, "utility_property": P2, "rate": 250}], "2027-03-20")

		self.govern(draft)

		self.assertEqual(draft.items[0].utility_service_request, self.u3.name)

	def test_a_rent_month_is_blocked_whatever_carries_the_request(self):
		old = submitted_invoice([{"item_code": P1, "rate": 1000}], "2027-03-01")
		draft = make_invoice([{"item_code": P1}], "2027-03-20")

		with self.assertRaisesRegex(frappe.ValidationError, old.name):
			self.govern(draft)

	@needs_column
	def test_a_new_invoice_blocks_the_same_month_of_its_line_request(self):
		new = submitted_invoice([{"item_code": ELECTRICITY, "rate": 250, "utility_service_request": self.u3.name}], "2027-03-01")
		draft = make_invoice([{"item_code": ELECTRICITY, "utility_property": P2, "rate": 250}], "2027-03-20")

		with self.assertRaisesRegex(frappe.ValidationError, new.name):
			self.govern(draft)

	@needs_column
	def test_mixed_old_and_new_invoices_both_block(self):
		submitted_invoice([{"item_code": ELECTRICITY, "rate": 200}], "2027-03-01", header=self.u1.name)
		submitted_invoice([{"item_code": ELECTRICITY, "rate": 250, "utility_service_request": self.u3.name}], "2027-04-01")

		for posting_date, property_name, rate in (("2027-03-20", P1, 200), ("2027-04-20", P2, 250)):
			draft = make_invoice([{"item_code": ELECTRICITY, "utility_property": property_name, "rate": rate}], posting_date)
			with self.assertRaisesRegex(frappe.ValidationError, "already invoiced"):
				self.govern(draft)


class TestContractChecks(LineRequestCase):
	"""Require Contract, checked once per request on the invoice."""

	def setUp(self):
		super().setUp()
		fx.use_approach("Item Price", require_contract=1, require_signed=1)

	def validate(self, invoice):
		sales_invoice.validate(invoice)

	def two_requests(self):
		return make_invoice([{"item_code": P1}, {"item_code": P2}], "2027-03-10")

	def test_every_request_on_the_invoice_needs_its_contract(self):
		fx.make_contract(self.u1.name)

		with self.assertRaisesRegex(frappe.ValidationError, f"{self.u3.name}</strong> has no signed, submitted Contract"):
			self.validate(self.two_requests())

	def test_an_unsigned_contract_of_one_request_is_refused(self):
		fx.make_contract(self.u1.name)
		fx.make_contract(self.u3.name, signed=False)

		with self.assertRaisesRegex(frappe.ValidationError, self.u3.name):
			self.validate(self.two_requests())

	def test_both_contracts_let_it_through(self):
		fx.make_contract(self.u1.name)
		fx.make_contract(self.u3.name)

		invoice = self.two_requests()
		self.validate(invoice)

		self.assertEqual([row.utility_service_request for row in invoice.items], [self.u1.name, self.u3.name])

	def test_each_request_is_checked_once(self):
		fx.make_contract(self.u1.name)
		fx.make_contract(self.u3.name)
		invoice = make_invoice([{"item_code": P1}, {"item_code": P2}, {"item_code": ELECTRICITY, "utility_property": P2, "rate": 250}], "2027-03-10")

		with patch.object(sales_invoice, "check_service_request_contract", wraps=sales_invoice.check_service_request_contract) as check:
			self.validate(invoice)

		self.assertEqual(sorted(call.args[1] for call in check.call_args_list), [self.u1.name, self.u3.name])

	def test_an_old_header_is_still_checked(self):
		invoice = frappe._dict(utility_service_request=self.u1.name, is_return=0)

		with self.assertRaisesRegex(frappe.ValidationError, self.u1.name):
			sales_invoice.check_service_request_contract(invoice)


class TestCostCenters(LineRequestCase):
	def setUp(self):
		super().setUp()
		company = fx.company()
		from utility_billing.utility_billing.tests import factories

		self.center_1 = factories.ensure_cost_center("_Test Line USR Center 1", company)
		self.center_2 = factories.ensure_cost_center("_Test Line USR Center 2", company)
		frappe.db.set_value("Utility Property", P1, "cost_center", self.center_1)
		frappe.db.set_value("Utility Property", P2, "cost_center", self.center_2)
		# The requests were made before: clear their rows' cost centers, so the property's apply
		frappe.db.sql(
			"update `tabUtility Service Request Item` set cost_center=null where parent in %s",
			[(self.u1.name, self.u3.name)],
		)

	def test_lines_of_two_requests_take_their_own_property_cost_center(self):
		invoice = make_invoice([{"item_code": P1}, {"item_code": P2}, {"item_code": ELECTRICITY, "utility_property": P2, "rate": 250}], "2027-03-10")

		sales_invoice.validate(invoice)

		self.assertEqual([row.cost_center for row in invoice.items], [self.center_1, self.center_2, self.center_2])

	def test_an_ordinary_line_with_a_property_takes_its_cost_center(self):
		invoice = make_invoice([{"item_code": OTHER_ITEM, "rate": 5, "utility_property": P2}], "2027-03-10")

		sales_invoice.validate(invoice)

		self.assertEqual(invoice.items[0].cost_center, self.center_2)
		self.assertIsNone(invoice.items[0].get("utility_service_request"))

	def test_a_draft_keeping_its_header_is_filled_as_before(self):
		invoice = make_invoice(
			[{"item_code": P1}, {"item_code": OTHER_ITEM, "rate": 5, "utility_property": P2}],
			"2027-03-10",
			header=self.u1.name,
			auto_repeat="_Test AR",
		)

		sales_invoice.validate(invoice)

		self.assertEqual(invoice.items[0].cost_center, self.center_1)
		self.assertNotEqual(invoice.items[1].cost_center, self.center_2)


class TestDailyJob(LineRequestCase):
	def setUp(self):
		super().setUp()
		frappe.db.set_value(
			"Contract Utility Property Item",
			self.u1.requested_properties[0].name,
			{"enable_auto_billing": 1, "billing_date_type": "First Day of Month"},
		)
		frappe.db.sql(
			"update `tabUtility Service Request Item` set utility_property=%s where parent=%s and item_code=%s",
			(P1, self.u1.name, P1),
		)

	def test_the_draft_carries_the_request_on_its_line(self):
		with captured_inserts("Sales Invoice") as inserted, patch.object(auto_repeat, "today", return_value="2027-03-01"):
			auto_repeat.create_item_price_sales_invoices()

		drafts = [doc for doc in inserted if self.u1.name in (doc.remarks or "")]
		self.assertEqual(len(drafts), 1)
		self.assertIsNone(drafts[0].get("utility_service_request"))
		self.assertEqual(
			(drafts[0].items[0].utility_service_request, drafts[0].items[0].utility_property), (self.u1.name, P1)
		)
		self.assertIsNone(frappe.db.get_value("Sales Invoice", drafts[0].name, "utility_service_request"))


class TestLeaseMove(LineRequestCase):
	def move_u1_end(self):
		self.u1.reload()
		self.u1.end_date = "2027-05-01"
		self.u1.requested_properties[0].end_date = "2027-04-30"
		self.u1.save(ignore_permissions=True)

	def test_an_old_invoice_after_the_new_end_blocks_the_move(self):
		old = submitted_invoice([{"item_code": P1, "rate": 1000}], "2027-06-01", header=self.u1.name)

		with self.assertRaisesRegex(frappe.ValidationError, old.name):
			self.move_u1_end()

	@needs_column
	def test_a_new_invoice_after_the_new_end_blocks_the_move(self):
		new = submitted_invoice([{"item_code": P1, "rate": 1000, "utility_service_request": self.u1.name}], "2027-06-01")

		with self.assertRaisesRegex(frappe.ValidationError, new.name):
			self.move_u1_end()

	@needs_column
	def test_an_invoice_of_the_next_request_does_not_block(self):
		submitted_invoice([{"item_code": P1, "rate": 1200, "utility_service_request": self.u2.name}], "2027-07-01")

		self.move_u1_end()


class TestPenaltyJob(LineRequestCase):
	def setUp(self):
		super().setUp()
		rule = frappe.get_doc(
			{
				"doctype": "Billing Adjustment Rule",
				"rule_name": "_Test Line USR Penalty",
				"frequency": "Monthly",
				"penalty_type": "Fixed Amount",
				"penalty_value": 50,
				"penalty_frequency": "Monthly",
				"grace_period_days": 0,
			}
		).insert(ignore_permissions=True)
		for request in (self.u1, self.u3):
			frappe.db.set_value("Contract Utility Property Item", request.requested_properties[0].name, "adjustment_rule", rule.name)

	def penalties(self):
		with patch.object(auto_repeat, "create_penalty_invoice") as create:
			auto_repeat.process_penalties_for_overdue_invoices()

		return {call.args[0].name: (call.args[1], [item["utility_property"] for item in call.args[3]]) for call in create.call_args_list}

	def overdue(self, lines, header=None):
		return submitted_invoice(lines, "2027-03-01", header=header, status="Overdue", due_date=add_days(today(), -90))

	def test_an_old_invoice_takes_the_rules_of_its_header_request(self):
		old = self.overdue([{"item_code": P1, "rate": 1000, "utility_property": P1}], header=self.u1.name)

		self.assertEqual(self.penalties().get(old.name), (self.u1.name, [P1]))

	@needs_column
	def test_a_new_invoice_takes_the_rules_of_each_line_request(self):
		new = self.overdue(
			[
				{"item_code": P1, "rate": 1000, "utility_property": P1, "utility_service_request": self.u1.name},
				{"item_code": P2, "rate": 2000, "utility_property": P2, "utility_service_request": self.u3.name},
			]
		)

		self.assertEqual(self.penalties().get(new.name), (None, [P1, P2]))


class TestAutoRepeatCopy(LineRequestCase):
	"""A draft Auto Repeat makes from a new invoice: blank header, requests on the lines."""

	def copy(self, reference, posting_date):
		draft = frappe.copy_doc(reference)
		draft.posting_date = posting_date
		draft.auto_repeat = "_Test AR"
		draft.on_recurring(reference_doc=reference, auto_repeat_doc=frappe._dict())
		return draft

	def reference(self):
		reference = make_invoice(
			[{"item_code": P1}, {"item_code": ELECTRICITY, "utility_property": P2, "rate": 250}], "2027-06-10"
		)
		self.govern(reference)
		self.assertEqual([row.utility_service_request for row in reference.items], [self.u1.name, self.u3.name])
		return reference

	def test_a_line_with_a_property_finds_its_request_again(self):
		draft = self.copy(self.reference(), "2027-07-10")

		self.assertIsNone(draft.items[0].get("utility_service_request"))
		self.govern(draft)

		self.assertIsNone(draft.utility_service_request)
		self.assertEqual([row.utility_service_request for row in draft.items], [self.u2.name, self.u3.name])
		self.assertEqual([row.rate for row in draft.items], [1200, 250])

	def test_a_copy_past_every_lease_is_refused(self):
		draft = self.copy(self.reference(), "2028-02-10")

		with self.assertRaisesRegex(frappe.ValidationError, "leases"):
			self.govern(draft)

	@needs_column
	def test_a_request_picked_on_a_line_without_property_is_kept(self):
		n1 = make_request([], "2027-01-01", "2028-01-01", [(ELECTRICITY, 200)], customer=OTHER_CUSTOMER)
		n2 = make_request([], "2027-01-01", "2028-01-01", [(ELECTRICITY, 300)], customer=OTHER_CUSTOMER)
		reference = make_invoice(
			[{"item_code": ELECTRICITY, "rate": 300, "utility_service_request": n2.name}], "2027-06-10", customer=OTHER_CUSTOMER
		)
		self.govern(reference)

		draft = self.copy(reference, "2027-07-10")
		self.govern(draft)

		self.assertEqual(draft.items[0].utility_service_request, n2.name)
		self.assertNotEqual(draft.items[0].utility_service_request, n1.name)


class TestColumnGuard(LineRequestCase):
	def test_queries_read_the_header_until_the_column_exists(self):
		self.assertEqual(line_requests_stored(), has_line_column())
