"""Unit tests for the portal payment amount and redirect helpers."""

from frappe.tests import UnitTestCase

from utility_billing.api.portal.payment_service import (
	clean_phone,
	payable_amount,
	safe_redirect,
)


class TestPayableAmount(UnitTestCase):
	"""Amount a customer can still pay on a listed document."""

	def test_invoice_uses_the_outstanding_amount(self):
		invoice = {
			"currency": "KES",
			"party_account_currency": "KES",
			"outstanding_amount": 2500,
			"conversion_rate": 1,
		}
		self.assertEqual(payable_amount(invoice, "Sales Invoice"), 2500)

	def test_order_uses_the_unbilled_balance(self):
		order = {
			"currency": "KES",
			"party_account_currency": "KES",
			"rounded_total": 12000,
			"advance_paid": 2000,
			"conversion_rate": 1,
		}
		self.assertEqual(payable_amount(order, "Sales Order"), 10000)

	def test_party_currency_is_converted_back(self):
		invoice = {
			"currency": "USD",
			"party_account_currency": "KES",
			"outstanding_amount": 130000,
			"conversion_rate": 130,
		}
		self.assertEqual(payable_amount(invoice, "Sales Invoice"), 1000)

	def test_settled_documents_are_zero_not_negative(self):
		order = {
			"currency": "KES",
			"party_account_currency": "KES",
			"rounded_total": 5000,
			"advance_paid": 6000,
			"conversion_rate": 1,
		}
		self.assertEqual(payable_amount(order, "Sales Order"), 0)


class TestRedirectSafety(UnitTestCase):
	"""Only same-site redirect targets are appended to a checkout URL."""

	def test_local_paths_are_allowed(self):
		self.assertEqual(safe_redirect("/invoices?tab=orders"), "/invoices?tab=orders")

	def test_external_and_protocol_relative_urls_are_rejected(self):
		for target in ("https://evil.example", "//evil.example", "invoices", None):
			self.assertIsNone(safe_redirect(target))

	def test_backslashes_are_rejected(self):
		self.assertIsNone(safe_redirect("/\\evil.example"))


class TestCleanPhone(UnitTestCase):
	"""Phone numbers are normalised for mobile money gateways."""

	def test_country_code_is_converted_to_local_format(self):
		self.assertEqual(clean_phone("+254 712 345 678"), "0712345678")

	def test_missing_number_returns_none(self):
		self.assertIsNone(clean_phone(None))
		self.assertIsNone(clean_phone(""))
