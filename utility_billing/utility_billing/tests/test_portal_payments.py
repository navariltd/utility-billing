"""Unit tests for the portal payment amount, redirect and gateway helpers."""

import frappe
from frappe.tests import UnitTestCase

from utility_billing.api.portal.payment_service import (
	build_payment_details,
	clean_phone,
	payable_amount,
	safe_redirect,
)


class TestPaymentDetails(UnitTestCase):
	"""Gateway checkout arguments are built from the reference document."""

	def setUp(self):
		self.reference_doc = frappe._dict(doctype="Sales Invoice", name="SINV-0001", currency="KES")
		self.account = frappe._dict(payment_gateway="Mpesa-Test")

	def test_reference_document_and_gateway_are_passed_to_the_controller(self):
		details = build_payment_details(
			self.reference_doc,
			self.account,
			2500,
			"Jane Doe",
			"jane@example.com",
			redirect_to="/bookings",
		)

		self.assertEqual(details["reference_doctype"], "Sales Invoice")
		self.assertEqual(details["reference_docname"], "SINV-0001")
		self.assertEqual(details["amount"], 2500)
		self.assertEqual(details["currency"], "KES")
		self.assertEqual(details["payment_gateway"], "Mpesa-Test")
		self.assertEqual(details["redirect_to"], "/bookings")
		self.assertNotIn("phone_number", details)

	def test_external_redirect_is_dropped(self):
		details = build_payment_details(
			self.reference_doc,
			self.account,
			2500,
			"Jane Doe",
			"jane@example.com",
			redirect_to="https://evil.example",
		)

		self.assertEqual(details["redirect_to"], "")

	def test_phone_number_is_normalised(self):
		details = build_payment_details(
			self.reference_doc,
			self.account,
			2500,
			"Jane Doe",
			"jane@example.com",
			phone_number="+254 712 345 678",
		)

		self.assertEqual(details["phone_number"], "0712345678")


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
