"""Payment Request creation and amount helpers for the portal.

Kept separate from :mod:`utility_billing.api.portal.payments` so the public
endpoints stay small and the gateway/amount logic can be unit tested on its own.
"""

from urllib.parse import urlencode, urlparse

import frappe
from erpnext.accounts.doctype.payment_request.payment_request import get_amount
from frappe import _
from frappe.utils import flt, get_url, nowdate

OPEN_REQUEST_STATUSES = ("Requested", "Initiated", "Partially Paid")


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
		frappe.throw(
			_("No payment gateway is configured for {0}.").format(frappe.bold(company))
		)

	return account


def open_payment_request(reference_doctype: str, reference_name: str) -> dict | None:
	"""Return the newest open Payment Request of a reference document."""
	rows = frappe.db.get_all(
		"Payment Request",
		filters={
			"reference_doctype": reference_doctype,
			"reference_name": reference_name,
			"docstatus": 1,
			"status": ("in", OPEN_REQUEST_STATUSES),
		},
		fields=[
			"name",
			"status",
			"payment_url",
			"payment_channel",
			"payment_gateway_account",
			"grand_total",
			"outstanding_amount",
			"currency",
			"reference_doctype",
			"reference_name",
		],
		order_by="creation desc",
		limit=1,
	)
	return rows[0] if rows else None


def cancel_payment_request(name: str) -> None:
	"""Cancel an open Payment Request so a new one can replace it."""
	payment_request = frappe.get_doc("Payment Request", name)
	if payment_request.docstatus != 1 or payment_request.status in ("Paid", "Cancelled"):
		return

	payment_request.flags.ignore_permissions = True
	payment_request.cancel()


def create_payment_request(
	reference_doc, account, amount: float, channel: str, phone: str | None
):
	"""Create and submit the Payment Request for a gateway."""
	email_to = (
		phone
		if channel == "Phone"
		else frappe.db.get_value("User", frappe.session.user, "email") or frappe.session.user
	)

	payment_request = frappe.new_doc("Payment Request")
	payment_request.update(
		{
			"payment_request_type": "Inward",
			"transaction_date": nowdate(),
			"company": reference_doc.company,
			"party_type": "Customer",
			"party": reference_doc.customer,
			"party_name": reference_doc.get("customer_name"),
			"reference_doctype": reference_doc.doctype,
			"reference_name": reference_doc.name,
			"grand_total": amount,
			"currency": reference_doc.currency,
			"party_account_currency": reference_doc.get("party_account_currency")
			or reference_doc.currency,
			"payment_gateway_account": account.name,
			"payment_gateway": account.payment_gateway,
			"payment_account": account.payment_account,
			"payment_channel": channel,
			"email_to": email_to,
			"phone_number": phone,
			"subject": _("Payment for {0} {1}").format(
				reference_doc.doctype, reference_doc.name
			),
			"message": account.get("message")
			or _("Payment for {0} {1}").format(reference_doc.doctype, reference_doc.name),
			"mute_email": 1,
		}
	)
	payment_request.flags.ignore_permissions = True
	payment_request.insert()
	payment_request.submit()
	payment_request.reload()

	return payment_request


def payment_response(payment_request, redirect_to: str | None) -> dict:
	"""Build the portal response from a Payment Request document or row."""
	payment_url = absolute_url(payment_request.get("payment_url"))
	if payment_url:
		payment_url = append_redirect(payment_url, redirect_to)

	return {
		"payment_request": payment_request.get("name"),
		"status": payment_request.get("status"),
		"payment_url": payment_url,
		"channel": payment_request.get("payment_channel"),
		"amount": flt(payment_request.get("grand_total")),
		"outstanding_amount": flt(payment_request.get("outstanding_amount")),
		"currency": payment_request.get("currency"),
		"reference_doctype": payment_request.get("reference_doctype"),
		"reference_name": payment_request.get("reference_name"),
	}


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


def append_redirect(url: str, redirect_to: str | None) -> str:
	"""Append a safe portal redirect target to a checkout URL."""
	target = safe_redirect(redirect_to)
	if not target:
		return url

	separator = "&" if "?" in url else "?"
	return f"{url}{separator}{urlencode({'redirect_to': target})}"


def safe_redirect(redirect_to: str | None) -> str | None:
	"""Return a same-site path, rejecting absolute URLs."""
	if not redirect_to:
		return None

	target = str(redirect_to).strip()
	if not target.startswith("/") or target.startswith("//") or "\\" in target:
		return None

	return target
