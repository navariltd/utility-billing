"""Portal payments for tenancy invoices and order advances.

The portal never creates accounting entries or ``Payment Request`` documents
itself. It asks the selected gateway controller for a checkout URL and redirects
the customer there:

* a Sales Invoice is paid for its outstanding amount;
* a Sales Order is paid as an advance for its unbilled balance.

The gateway records the payment on the reference document when it confirms the
transaction, exactly as it does for the event booking flow.
"""

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import cint, flt

from utility_billing.api.portal.payment_service import (
	empty_documents,
	get_payment_url,
	payable_amount,
	reference_amount,
	resolve_gateway_account,
)
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

DETAIL_FIELDS = {
	"Sales Invoice": (
		"name",
		"customer",
		"customer_name",
		"posting_date",
		"due_date",
		"status",
		"company",
		"currency",
		"conversion_rate",
		"party_account_currency",
		"net_total",
		"total_taxes_and_charges",
		"grand_total",
		"rounded_total",
		"paid_amount",
		"outstanding_amount",
	),
	"Sales Order": (
		"name",
		"customer",
		"customer_name",
		"transaction_date",
		"delivery_date",
		"status",
		"company",
		"currency",
		"conversion_rate",
		"party_account_currency",
		"net_total",
		"total_taxes_and_charges",
		"grand_total",
		"rounded_total",
		"advance_paid",
	),
}

LINE_FIELDS = ("item_code", "item_name", "description", "qty", "uom", "rate", "amount")
TAX_FIELDS = ("description", "charge_type", "rate", "tax_amount")
METER_LINE_FIELDS = (
	"item_code",
	"meter_number",
	"previous_reading",
	"current_reading",
	"uom",
	"consumption",
	"meter_reading",
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
def get_customer_document(reference_doctype: str, reference_name: str) -> dict:
	"""Return one submitted invoice or order of the customer with its sections.

	Args:
		reference_doctype: ``Sales Invoice`` or ``Sales Order``.
		reference_name: Name of the submitted document.

	Returns:
		The document header fields plus ``lines``, ``taxes``,
		``meter_readings`` and its ``payable_amount``.

	Raises:
		frappe.DoesNotExistError: When the document does not exist, is not
			submitted or belongs to another Customer.
	"""
	require_authenticated_user()
	if reference_doctype not in SUPPORTED_DOCTYPES:
		frappe.throw(
			_("Documents are not supported for {0}.").format(reference_doctype),
			frappe.DoesNotExistError,
		)

	customers = {customer["name"] for customer in get_portal_customers()}
	document = frappe.db.get_value(
		reference_doctype,
		{"name": reference_name, "docstatus": 1},
		[*DETAIL_FIELDS[reference_doctype], "docstatus"],
		as_dict=True,
	)
	if not document or document.customer not in customers:
		frappe.throw(
			_("{0} {1} was not found.").format(_(reference_doctype), reference_name),
			frappe.DoesNotExistError,
		)

	document.doctype = reference_doctype
	document.lines = frappe.db.get_all(
		f"{reference_doctype} Item",
		filters={"parent": reference_name, "parenttype": reference_doctype},
		fields=list(LINE_FIELDS),
		order_by="idx asc",
	)
	document.taxes = frappe.db.get_all(
		"Sales Taxes and Charges",
		filters={"parent": reference_name, "parenttype": reference_doctype},
		fields=list(TAX_FIELDS),
		order_by="idx asc",
	)
	document.meter_readings = frappe.db.get_all(
		f"{reference_doctype} Meter Reading",
		filters={"parent": reference_name, "parenttype": reference_doctype},
		fields=list(METER_LINE_FIELDS),
		order_by="idx asc",
	)
	document.payable_amount = payable_amount(document, reference_doctype)

	return document


@frappe.whitelist()
def initiate_payment(
	reference_doctype: str,
	reference_name: str,
	gateway_account: str | None = None,
	phone_number: str | None = None,
	redirect_to: str | None = None,
) -> dict:
	"""Return the gateway checkout URL for a submitted document.

	The portal redirects the customer straight to the returned URL; no
	``Payment Request`` is created. The gateway records the payment on the
	reference document when it confirms the transaction.

	Args:
		reference_doctype: ``Sales Invoice`` or ``Sales Order``.
		reference_name: Submitted document to pay.
		gateway_account: ``Payment Gateway Account`` name; the company default
			is used when omitted.
		phone_number: Optional payer phone for phone-based gateways (M-Pesa).
		redirect_to: Portal path to return to after an external checkout.

	Returns:
		Dict with ``payment_url``, amount, currency, gateway and channel.

	Raises:
		frappe.PermissionError: When the document belongs to another Customer.
		frappe.ValidationError: When the document is not payable or no gateway
			is configured for its company.
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

	payment_url = get_payment_url(
		ref_doc,
		account,
		amount,
		redirect_to=redirect_to,
		phone_number=phone_number,
	)

	return {
		"payment_url": payment_url,
		"reference_doctype": ref_doc.doctype,
		"reference_name": ref_doc.name,
		"amount": amount,
		"currency": ref_doc.currency,
		"channel": account.payment_channel or "Email",
		"payment_gateway": account.payment_gateway,
	}
