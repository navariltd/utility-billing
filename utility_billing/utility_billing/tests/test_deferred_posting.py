"""Integration tests for the deferred posting of Sales Invoice lines.

Verifies that a line with a Deferred Posting Date credits the deferred account of
its company instead of its income account, that the revenue reaches the income
account through a Deferred Revenue Journal Entry referencing the invoice, and
that cancelling the invoice cancels that Journal Entry. A line whose Deferred
Posting Date is set while deferred posting is switched off posts as usual.
"""

import frappe
from erpnext.accounts.party import get_party_account
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, add_months, flt, today

from utility_billing.utility_billing.tests.factories import ensure_customer, ensure_item
from utility_billing.utility_billing.utils.deferred_posting import (
	DEFERRED_ACCOUNT_FIELD,
	JOURNAL_ENTRY_FIELD,
	POSTING_DATE_FIELD,
)

TEST_COMPANY = "_Test Company"
TEST_INCOME_ACCOUNT = "_Test Account Sales"
TEST_DEFERRED_ACCOUNT = "_Test Deferred Revenue"
TEST_CUSTOMER = "_Test Deferred Posting Customer"
TEST_ITEM = "_Test Deferred Posting Item"
TEST_ITEM_2 = "_Test Deferred Posting Item 2"
TEST_PRICE_LIST = "_Test Deferred Posting Price List"
AMOUNT = 1000.0
SETTINGS_DOCTYPE = "Utility Billing Settings"


class TestDeferredPosting(FrappeTestCase):
	"""Deferred posting of Sales Invoice lines."""

	# Deferred posting is switched on for the tests and the settings written by a
	# run are restored afterwards, so a site that uses the feature keeps the
	# configuration it had.
	original_enabled = None
	created_mappings: list[str] = []

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.original_enabled = frappe.db.get_single_value(SETTINGS_DOCTYPE, "enable_deferred_posting")
		cls.created_mappings = []

	@classmethod
	def tearDownClass(cls):
		super().tearDownClass()

		for name in cls.created_mappings:
			frappe.db.delete("Utility Deferred Account", {"name": name})

		frappe.db.set_single_value(
			SETTINGS_DOCTYPE, "enable_deferred_posting", cls.original_enabled or 0
		)
		frappe.clear_cache(doctype=SETTINGS_DOCTYPE)

	def setUp(self):
		super().setUp()
		self.company = self._get_company()
		self.cost_center = frappe.db.get_value("Company", self.company, "cost_center")
		self.income_account = self._get_income_account()
		self.deferred_account = self._ensure_deferred_account()
		self.customer = ensure_customer(TEST_CUSTOMER)
		self.item = ensure_item(TEST_ITEM)
		self.price_list = self._ensure_price_list()
		self.deferred_date = str(add_days(today(), 30))
		self._enable_deferred_posting()

	def test_deferred_line_credits_the_deferred_account(self):
		invoice = self._make_invoice()

		self.assertEqual(invoice.items[0].income_account, self.income_account)

		gle = frappe.db.get_value(
			"GL Entry",
			{
				"voucher_type": "Sales Invoice",
				"voucher_no": invoice.name,
				"account": self.deferred_account,
			},
			["credit", "posting_date"],
			as_dict=True,
		)
		self.assertTrue(gle, "The deferred account was not credited by the invoice")
		self.assertEqual(flt(gle.credit), AMOUNT)
		self.assertEqual(str(gle.posting_date), today())

		self.assertFalse(
			frappe.db.exists(
				"GL Entry",
				{
					"voucher_type": "Sales Invoice",
					"voucher_no": invoice.name,
					"account": self.income_account,
				},
			),
			"The income account was credited although the line is deferred",
		)

	def test_line_posting_on_the_invoice_date_goes_to_the_income_account(self):
		"""A line whose posting date was filled with the invoice date posts as usual."""
		invoice = self._make_invoice(deferred_date="")

		self.assertEqual(invoice.items[0].get(POSTING_DATE_FIELD), today())
		self.assertIsNone(invoice.items[0].get(DEFERRED_ACCOUNT_FIELD))
		self.assertTrue(
			frappe.db.exists(
				"GL Entry",
				{
					"voucher_type": "Sales Invoice",
					"voucher_no": invoice.name,
					"account": self.income_account,
				},
			)
		)
		self.assertFalse(
			frappe.db.exists(
				"GL Entry",
				{
					"voucher_type": "Sales Invoice",
					"voucher_no": invoice.name,
					"account": self.deferred_account,
				},
			)
		)
		self.assertFalse(self._journal_entry_of(invoice))

	def test_posting_dates_are_filled_for_repeated_items(self):
		"""Lines without a posting date follow the invoice date, month by month.

		The first line of an item posts with the invoice, every further line of the
		same item one month later, a date set by hand is kept and every item has
		its own sequence.
		"""
		other_item = ensure_item(TEST_ITEM_2)
		by_hand = str(add_months(today(), 5))

		invoice = self._make_invoice_with_lines(
			[
				{"item_code": self.item},
				{"item_code": self.item},
				{"item_code": other_item},
				{"item_code": self.item, "posting_date": by_hand},
				{"item_code": self.item},
			]
		)

		self.assertEqual(
			[row.get(POSTING_DATE_FIELD) for row in invoice.items],
			[today(), str(add_months(today(), 1)), today(), by_hand, str(add_months(today(), 3))],
		)

		# Only the lines posting after the invoice are deferred.
		self.assertIsNone(self._journal_entry_of_row(invoice.items[0]))
		self.assertTrue(self._journal_entry_of_row(invoice.items[1]))
		self.assertIsNone(self._journal_entry_of_row(invoice.items[2]))
		self.assertTrue(self._journal_entry_of_row(invoice.items[3]))
		self.assertTrue(self._journal_entry_of_row(invoice.items[4]))

		self.assertEqual(
			[row.get(DEFERRED_ACCOUNT_FIELD) for row in invoice.items],
			[None, self.deferred_account, None, self.deferred_account, self.deferred_account],
		)

		deferred_credit = sum(
			flt(credit)
			for credit in frappe.get_all(
				"GL Entry",
				filters={
					"voucher_type": "Sales Invoice",
					"voucher_no": invoice.name,
					"account": self.deferred_account,
				},
				pluck="credit",
			)
		)
		self.assertEqual(deferred_credit, AMOUNT * 3)

	def test_revenue_is_recognised_on_the_deferred_posting_date(self):
		invoice = self._make_invoice()
		journal_entry_name = self._journal_entry_of(invoice)
		self.assertTrue(journal_entry_name, "No Journal Entry was created for the deferred line")

		journal_entry = frappe.get_doc("Journal Entry", journal_entry_name)
		self.assertEqual(journal_entry.docstatus, 1)
		self.assertEqual(journal_entry.company, self.company)
		self.assertEqual(journal_entry.voucher_type, "Deferred Revenue")
		self.assertEqual(str(journal_entry.posting_date), self.deferred_date)

		self.assertEqual(invoice.items[0].deferred_revenue_account, self.deferred_account)
		self.assertEqual(invoice.items[0].get(DEFERRED_ACCOUNT_FIELD), self.deferred_account)

		for row in journal_entry.accounts:
			self.assertEqual(row.reference_type, "Sales Invoice")
			self.assertEqual(row.reference_name, invoice.name)
			self.assertEqual(row.reference_detail_no, invoice.items[0].name)

		rows = {row.account: row for row in journal_entry.accounts}
		self.assertEqual(flt(rows[self.deferred_account].debit), AMOUNT)
		self.assertEqual(flt(rows[self.income_account].credit), AMOUNT)
		self.assertEqual(rows[self.income_account].cost_center, self.cost_center)

		gle = frappe.db.get_value(
			"GL Entry",
			{
				"voucher_type": "Journal Entry",
				"voucher_no": journal_entry_name,
				"account": self.income_account,
			},
			["credit", "posting_date"],
			as_dict=True,
		)
		self.assertEqual(flt(gle.credit), AMOUNT)
		self.assertEqual(str(gle.posting_date), self.deferred_date)

	def test_cancelling_the_invoice_cancels_the_journal_entry(self):
		invoice = self._make_invoice()
		journal_entry_name = self._journal_entry_of(invoice)
		self.assertTrue(journal_entry_name)

		invoice.cancel()

		self.assertEqual(frappe.db.get_value("Journal Entry", journal_entry_name, "docstatus"), 2)

	def test_line_posts_normally_when_deferred_posting_is_disabled(self):
		self._disable_deferred_posting()

		invoice = self._make_invoice()

		self.assertTrue(
			frappe.db.exists(
				"GL Entry",
				{
					"voucher_type": "Sales Invoice",
					"voucher_no": invoice.name,
					"account": self.income_account,
				},
			),
			"The income account was not credited although deferring is switched off",
		)
		self.assertFalse(
			frappe.db.exists(
				"GL Entry",
				{
					"voucher_type": "Sales Invoice",
					"voucher_no": invoice.name,
					"account": self.deferred_account,
				},
			)
		)
		self.assertFalse(self._journal_entry_of(invoice))

	def test_deferred_posting_date_before_the_invoice_date_is_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			self._make_invoice(deferred_date=str(add_days(today(), -1)))

	def _make_invoice(self, deferred_date: str | None = None):
		"""Create and submit an invoice holding a single line."""
		posting_date = self.deferred_date if deferred_date is None else deferred_date

		return self._make_invoice_with_lines([{"posting_date": posting_date}])

	def _make_invoice_with_lines(self, lines: list[dict]):
		"""Create and submit an invoice with the given line overrides."""
		invoice = self._new_invoice()

		for line in lines:
			invoice.append("items", self._line(**line))

		invoice.insert()
		invoice.submit()

		return invoice

	def _new_invoice(self):
		"""Return an unsaved invoice of the test company and customer."""
		company_currency = frappe.db.get_value("Company", self.company, "default_currency")

		invoice = frappe.new_doc("Sales Invoice")
		invoice.flags.ignore_permissions = True
		invoice.company = self.company
		invoice.customer = self.customer
		invoice.debit_to = get_party_account("Customer", self.customer, self.company)
		invoice.posting_date = today()
		invoice.due_date = today()
		invoice.update_stock = 0
		invoice.selling_price_list = self.price_list
		invoice.currency = company_currency
		invoice.conversion_rate = 1
		invoice.price_list_currency = company_currency
		invoice.plc_conversion_rate = 1

		return invoice

	def _line(self, item_code: str | None = None, posting_date: str | None = None):
		"""Return an invoice line of the test item, with an optional posting date."""
		line = {
			"item_code": item_code or self.item,
			"qty": 1,
			"rate": AMOUNT,
			"income_account": self.income_account,
			"cost_center": self.cost_center,
		}
		if posting_date:
			line[POSTING_DATE_FIELD] = posting_date

		return line

	def _journal_entry_of(self, invoice) -> str | None:
		"""Return the Journal Entry stored on the first line of an invoice."""
		return self._journal_entry_of_row(invoice.items[0])

	def _journal_entry_of_row(self, row) -> str | None:
		"""Return the Journal Entry stored on an invoice line."""
		return frappe.db.get_value("Sales Invoice Item", row.name, JOURNAL_ENTRY_FIELD)

	def _get_company(self) -> str:
		company = frappe.db.get_value("Company", {"name": TEST_COMPANY}, "name")
		company = company or frappe.db.get_value("Company", {}, "name")

		if not company:
			self.skipTest("No company available to post a Sales Invoice")

		return company

	def _get_income_account(self) -> str:
		account = frappe.db.get_value(
			"Account", {"company": self.company, "account_name": TEST_INCOME_ACCOUNT}, "name"
		)
		account = account or frappe.db.get_value("Company", self.company, "default_income_account")

		if not account:
			self.skipTest(f"Company {self.company} has no income account")

		return account

	def _ensure_price_list(self) -> str:
		"""Return a selling price list in the company currency.

		A Sales Invoice requires a selling price list whose currency matches the
		transaction currency, so a price list is created when the site only has
		price lists in another currency.
		"""
		currency = frappe.db.get_value("Company", self.company, "default_currency")

		existing = frappe.db.get_value(
			"Price List", {"selling": 1, "enabled": 1, "currency": currency}, "name"
		)
		if existing:
			return existing

		name = f"{TEST_PRICE_LIST} {currency}"
		price_list = frappe.new_doc("Price List")
		price_list.flags.ignore_permissions = True
		price_list.price_list_name = name
		price_list.currency = currency
		price_list.selling = 1
		price_list.enabled = 1
		price_list.insert()

		return price_list.name

	def _ensure_deferred_account(self) -> str:
		"""Return the test deferred account, creating it when missing."""
		account = frappe.db.get_value(
			"Account", {"company": self.company, "account_name": TEST_DEFERRED_ACCOUNT}, "name"
		)
		if account:
			return account

		parent_account = frappe.db.get_value(
			"Account",
			{"company": self.company, "account_name": "Current Liabilities", "is_group": 1},
			"name",
		)
		if not parent_account:
			self.skipTest(f"Company {self.company} has no current liabilities group account")

		account_doc = frappe.new_doc("Account")
		account_doc.flags.ignore_permissions = True
		account_doc.account_name = TEST_DEFERRED_ACCOUNT
		account_doc.company = self.company
		account_doc.parent_account = parent_account
		account_doc.account_type = "Temporary"
		account_doc.is_group = 0
		account_doc.insert()

		return account_doc.name

	def _enable_deferred_posting(self) -> None:
		"""Map the deferred account of the company in the settings.

		The single and its child table are written directly so that saving the
		settings, which also maintains the tenancy notification, is not needed.
		"""
		frappe.db.set_single_value(SETTINGS_DOCTYPE, "enable_deferred_posting", 1)

		configured = frappe.db.exists(
			"Utility Deferred Account",
			{
				"parent": SETTINGS_DOCTYPE,
				"company": self.company,
				"deferred_account": self.deferred_account,
			},
		)
		if not configured:
			row = frappe.get_doc(
				{
					"doctype": "Utility Deferred Account",
					"parent": SETTINGS_DOCTYPE,
					"parenttype": SETTINGS_DOCTYPE,
					"parentfield": "deferred_accounts",
					"company": self.company,
					"deferred_account": self.deferred_account,
				}
			)
			row.insert(ignore_permissions=True)
			type(self).created_mappings.append(row.name)

		frappe.clear_cache(doctype=SETTINGS_DOCTYPE)

	def _disable_deferred_posting(self) -> None:
		"""Switch deferred posting off, as the settings form does."""
		frappe.db.set_single_value(SETTINGS_DOCTYPE, "enable_deferred_posting", 0)
		frappe.clear_cache(doctype=SETTINGS_DOCTYPE)
