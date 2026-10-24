"""Portal payments for tenancy invoices and order advances.

The portal never creates accounting entries itself. It creates a standard
ERPNext ``Payment Request`` for the chosen gateway:

* a Sales Invoice is paid for its outstanding amount;
* a Sales Order is paid as an advance for its unbilled balance.

The gateway then returns a checkout URL (card/wallet gateways) or sends a
payment prompt to the customer's phone (M-Pesa). Payment Entries are created by
the gateway callback, exactly as they are for desk payments.
"""

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import cint, flt

from utility_billing.api.portal.payment_service import (
	cancel_payment_request,
	clean_phone,
	create_payment_request,
	empty_documents,
	open_payment_request,
	payable_amount,
	payment_response,
	reference_amount,
	resolve_gateway_account,
)
from utility_billing.api.portal.permissions import ignore_permissions
from utility_billing.api.portal.roles import get_portal_customers, require_authenticated_user

SUPPORTED_DOCTYPES = ("Sales Invoice", "Sales Order")

INVOICE_FIELDS = (
	"name",
	"posting_date",
	"due_date",
	"grand_total",
	"outstanding_amount",
	"currency",
	"conversion_rate",
	"party_account_currency",
	"status",
	"customer",
)

ORDER_FIELDS = (
	"name",
	"transaction_date",
	"delivery_date",
	"grand_total",
	"rounded_total",
	"advance_paid",
	"per_billed",
	"currency",
	"conversion_rate",
	"party_account_currency",
	"status",
	"customer",
)


@frappe.whitelist()
def get_payment_gateways() -> dict:
	"""Return the configured payment gateway accounts.

	Returns:
		Dict with ``gateways`` (name, gateway, currency, channel) and the
		companies they belong to.
	"""
	require_authenticated_user()

	accounts = frappe.db.get_all(
		"Payment Gateway Account",
		fields=[
			"name",
			"payment_gateway",
			"payment_account",
			"payment_channel",
			"currency",
			"company",
			"is_default",
			"message",
		],
		order_by="is_default desc, creation asc",
	)

	gateways = [
		{
			"name": account.name,
			"label": account.payment_gateway,
			"gateway": account.payment_gateway,
			"company": account.company,
			"channel": account.payment_channel or "Email",
			"currency": account.currency,
			"is_default": cint(account.is_default),
			"message": account.message,
		}
		for account in accounts
	]

	return {
		"gateways": gateways,
		"companies": sorted({gateway["company"] for gateway in gateways if gateway["company"]}),
	}


@frappe.whitelist()
def get_customer_documents() -> dict:
	"""Return every submitted, payable invoice and order of the customer.

	Returns:
		Dict with ``invoices``, ``orders`` and per-currency totals.
	"""
	require_authenticated_user()
	customers = get_portal_customers()
	if not customers:
		return empty_documents()

	names = [customer["name"] for customer in customers]
	invoices = frappe.db.get_all(
		"Sales Invoice",
		filters={
			"customer": ("in", names),
			"docstatus": 1,
			"outstanding_amount": (">", 0),
		},
		fields=list(INVOICE_FIELDS),
		order_by="posting_date desc",
		limit=200,
	)

	orders = frappe.db.get_all(
		"Sales Order",
		filters={
			"customer": ("in", names),
			"docstatus": 1,
			"status": ("not in", ["Closed", "Completed", "Cancelled"]),
		},
		fields=list(ORDER_FIELDS),
		order_by="transaction_date desc",
		limit=200,
	)

	for invoice in invoices:
		invoice["payable_amount"] = payable_amount(invoice, "Sales Invoice")
		invoice["payable"] = invoice["payable_amount"] > 0

	orders = [order for order in orders if payable_amount(order, "Sales Order") > 0]
	for order in orders:
		order["payable_amount"] = payable_amount(order, "Sales Order")
		order["payable"] = flt(order.get("per_billed")) < 100

	invoices = [invoice for invoice in invoices if invoice["payable"]]
	invoice_totals: dict[str, float] = defaultdict(float)
	order_totals: dict[str, float] = defaultdict(float)
	for invoice in invoices:
		invoice_totals[invoice.currency or ""] += invoice["payable_amount"]
	for order in orders:
		order_totals[order.currency or ""] += order["payable_amount"]

	return {
		"customer": names[0],
		"customers": customers,
		"invoices": invoices,
		"orders": orders,
		"totals": {
			"outstanding": dict(invoice_totals),
			"advances": dict(order_totals),
		},
	}


@frappe.whitelist()
def initiate_payment(
	reference_doctype: str,
	reference_name: str,
	gateway_account: str | None = None,
	phone_number: str | None = None,
	redirect_to: str | None = None,
) -> dict:
	"""Create a Payment Request and return its checkout URL or phone status.

	Args:
		reference_doctype: ``Sales Invoice`` or ``Sales Order``.
		reference_name: Submitted document to pay.
		gateway_account: ``Payment Gateway Account`` name; the company default
			is used when omitted.
		phone_number: Payer phone for phone-based gateways (M-Pesa).
		redirect_to: Portal path to return to after an external checkout.

	Returns:
		Dict with the Payment Request, checkout URL, status and amount.

	Raises:
		frappe.PermissionError: When the document belongs to another Customer.
		frappe.ValidationError: When the document is not payable, the gateway is
			not configured, or a phone number is missing for a phone gateway.
	"""
	require_authenticated_user()
	customers = {customer["name"] for customer in get_portal_customers()}
	if not customers:
		raise frappe.PermissionError

	if reference_doctype not in SUPPORTED_DOCTYPES:
		frappe.throw(_("Payments are not supported for {0}.").format(reference_doctype))

	ref_doc = frappe.get_doc(reference_doctype, reference_name)
	if ref_doc.customer not in customers:
		raise frappe.PermissionError

	if cint(ref_doc.docstatus) != 1:
		frappe.throw(_("Only submitted documents can be paid."))

	account = resolve_gateway_account(ref_doc.company, gateway_account)
	amount = reference_amount(ref_doc, account.payment_account)
	if amount <= 0:
		frappe.throw(_("There is nothing left to pay on this document."))

	channel = account.payment_channel or "Email"
	phone = clean_phone(phone_number)
	if channel == "Phone" and not phone:
		frappe.throw(_("Enter the phone number that will receive the payment prompt."))

	with ignore_permissions():
		existing = open_payment_request(reference_doctype, reference_name)
		if existing:
			reusable = (
				existing.payment_gateway_account == account.name
				and existing.payment_channel != "Phone"
				and existing.payment_url
				and flt(existing.grand_total) == amount
			)
			if reusable:
				return payment_response(existing, redirect_to)
			cancel_payment_request(existing.name)

		payment_request = create_payment_request(ref_doc, account, amount, channel, phone)

	return payment_response(payment_request, redirect_to)


@frappe.whitelist()
def get_payment_request_status(name: str) -> dict:
	"""Return the status of one of the caller's Payment Requests.

	Args:
		name: ``Payment Request`` name.

	Returns:
		Dict with status, amount and checkout URL.
	"""
	require_authenticated_user()
	customers = {customer["name"] for customer in get_portal_customers()}
	payment_request = frappe.get_doc("Payment Request", name)
	if payment_request.party not in customers:
		raise frappe.PermissionError

	return payment_response(payment_request, None)
