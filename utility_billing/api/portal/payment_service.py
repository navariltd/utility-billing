"""Gateway checkout helpers for the portal.

The portal does not create ``Payment Request`` documents. It asks the gateway
controller for a checkout URL and redirects the customer there, mirroring the
event booking flow: the gateway owns the transaction and records the payment on
the reference document when it confirms it.

Kept separate from :mod:`utility_billing.api.portal.payments` so the public
endpoints stay small and the gateway/amount logic can be unit tested on its own.
"""

from urllib.parse import urlparse

import frappe
from erpnext.accounts.doctype.payment_request.payment_request import get_amount
from frappe import _
from frappe.utils import flt, get_url


def empty_documents() -> dict:
	"""Document payload for users without a linked Customer."""
	return {
		"customer": None,
		"customers": [],
		"invoices": [],
		"orders": [],
		"totals": {"outstanding": {}, "advances": {}},
	}


def payable_amount(document: dict, doctype: str) -> float:
	"""Return the payable amount of a listed document in its currency."""
	currency = document.get("currency")
	party_currency = document.get("party_account_currency") or currency
	conversion_rate = flt(document.get("conversion_rate")) or 1

	if doctype == "Sales Invoice":
		amount = flt(document.get("outstanding_amount"))
	else:
		total = flt(document.get("rounded_total")) or flt(document.get("grand_total"))
		amount = total - flt(document.get("advance_paid"))

	if party_currency != currency:
		amount /= conversion_rate

	return max(amount, 0)


def reference_amount(reference_doc, payment_account: str | None) -> float:
	"""Return the amount still payable on a reference document."""
	return flt(get_amount(reference_doc, payment_account))


def resolve_gateway_account(company: str, gateway_account: str | None = None):
	"""Return the requested or default gateway account of a company.

	Raises:
		frappe.ValidationError: When no gateway is configured for the company.
	"""
	fields = [
		"name",
		"payment_gateway",
		"payment_account",
		"payment_channel",
		"company",
		"message",
	]
	if gateway_account:
		account = frappe.db.get_value(
			"Payment Gateway Account",
			{"name": gateway_account, "company": company},
			fields,
			as_dict=True,
		)
	else:
		account = frappe.db.get_value(
			"Payment Gateway Account",
			{"company": company, "is_default": 1},
			fields,
			as_dict=True,
		)
		if not account:
			account = frappe.db.get_value(
				"Payment Gateway Account",
				{"company": company},
				fields,
				as_dict=True,
			)

	if not account:
		frappe.throw(_("No payment gateway is configured for {0}.").format(frappe.bold(company)))

	return account


def build_payment_details(
	reference_doc,
	account,
	amount: float,
	payer_name: str | None,
	payer_email: str | None,
	redirect_to: str | None = None,
	phone_number: str | None = None,
) -> dict:
	"""Build the keyword arguments a gateway controller's URL builder expects.

	Args:
		reference_doc: Submitted document the payment settles.
		account: ``Payment Gateway Account`` row with ``payment_gateway``.
		amount: Amount to charge in the reference document's currency.
		payer_name: Customer name shown on the checkout page.
		payer_email: Customer email the gateway receipt goes to.
		redirect_to: Same-site portal path to return to after checkout.
		phone_number: Optional payer phone for phone-based gateways.

	Returns:
		Dict of checkout arguments, including a sanitised redirect target.
	"""
	reference_label = f"{reference_doc.doctype} {reference_doc.name}"
	details = {
		"amount": amount,
		"title": _("Payment for {0}").format(reference_label),
		"description": _("{0}'s payment for {1}").format(payer_name or payer_email, reference_label),
		"reference_doctype": reference_doc.doctype,
		"reference_docname": reference_doc.name,
		"payer_email": payer_email or frappe.session.user,
		"payer_name": payer_name or payer_email or frappe.session.user,
		"currency": reference_doc.currency,
		"payment_gateway": account.payment_gateway,
		"redirect_to": safe_redirect(redirect_to) or "",
	}

	phone = clean_phone(phone_number)
	if phone:
		details["phone_number"] = phone

	return details


def get_payment_url(
	reference_doc,
	account,
	amount: float,
	redirect_to: str | None = None,
	phone_number: str | None = None,
) -> str:
	"""Return the gateway checkout URL for a reference document.

	No ``Payment Request`` is created: the gateway receives the reference
	document itself and records the payment when it confirms the transaction.

	Raises:
		frappe.ValidationError: When the gateway rejects the currency, amount or
			checkout request.
	"""
	from payments.utils import get_payment_gateway_controller

	controller = get_payment_gateway_controller(account.payment_gateway)
	currency = reference_doc.currency

	if hasattr(controller, "validate_transaction_currency"):
		controller.validate_transaction_currency(currency)
	if hasattr(controller, "validate_minimum_transaction_amount"):
		controller.validate_minimum_transaction_amount(currency, amount)

	payer = (
		frappe.db.get_value("User", frappe.session.user, ["full_name", "email"], as_dict=True)
		or frappe._dict()
	)

	payment_details = build_payment_details(
		reference_doc,
		account,
		amount,
		payer.get("full_name"),
		payer.get("email"),
		redirect_to=redirect_to,
		phone_number=phone_number,
	)

	if account.payment_gateway in ("Razorpay", "Paymob"):
		order = controller.create_order(**payment_details)
		payment_details["order_id"] = order.get("id")

	url = absolute_url(controller.get_payment_url(**payment_details))
	if not url:
		frappe.throw(_("The payment gateway did not return a checkout URL."))

	return url


def clean_phone(phone_number: str | None) -> str | None:
	"""Return a phone number in the local format used by mobile gateways."""
	if not phone_number:
		return None

	digits = "".join(character for character in str(phone_number) if character.isdigit())
	if digits.startswith("254") and len(digits) > 9:
		digits = "0" + digits[3:]

	return digits or None


def absolute_url(url: str | None) -> str | None:
	"""Turn the relative URL returned by a gateway into an absolute URL."""
	if not url:
		return None

	url = url[2:] if url.startswith("./") else url
	if urlparse(url).scheme:
		return url

	return get_url("/" + url.lstrip("/"))


def safe_redirect(redirect_to: str | None) -> str | None:
	"""Return a same-site path, rejecting absolute URLs."""
	if not redirect_to:
		return None

	target = str(redirect_to).strip()
	if not target.startswith("/") or target.startswith("//") or "\\" in target:
		return None

	return target
