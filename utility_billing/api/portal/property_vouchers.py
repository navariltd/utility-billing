"""Sales Orders, Sales Invoices and Payment Entries of a property.

Companion module to :mod:`utility_billing.api.portal.property_documents`: it
resolves the billing vouchers that belong to a property and to the caller's own
Customers, plus the payment entries allocated against them.

A property is reached from a voucher through the meter readings it references
(``Sales Invoice Item.meter_reading``, ``Sales Invoice Meter Reading.meter_reading``
and the Sales Order equivalents) or through its ``utility_service_request``
header link. ``Payment Entry`` has no property link of its own; it is reached
through ``Payment Entry Reference`` rows pointing at those vouchers.

Permissions are bypassed deliberately (query builder / ``frappe.db``) because
Website Users have no read access to billing doctypes — callers must scope the
queries by their own Customers, which every function here does.
"""

import frappe
from frappe.query_builder import DocType, Order

#: Child doctypes that reference a meter reading, mapped to their link field.
METER_READING_LINKS = (
	("Sales Invoice Meter Reading", "meter_reading"),
	("Sales Invoice Item", "meter_reading"),
	("Sales Order Meter Reading", "meter_reading"),
	("Sales Order Item", "meter_reading"),
)

SALES_INVOICE_FIELDS = (
	"name",
	"posting_date",
	"due_date",
	"grand_total",
	"outstanding_amount",
	"status",
	"docstatus",
	"currency",
	"customer",
)

SALES_ORDER_FIELDS = (
	"name",
	"transaction_date",
	"delivery_date",
	"grand_total",
	"status",
	"docstatus",
	"currency",
	"customer",
)

PAYMENT_ENTRY_FIELDS = (
	"name",
	"posting_date",
	"payment_type",
	"mode_of_payment",
	"paid_amount",
	"received_amount",
	"paid_from_account_currency",
	"paid_to_account_currency",
	"reference_no",
	"status",
	"docstatus",
	"party",
)


def get_sales_orders(
	customer_names: list[str],
	meter_reading_names: list[str],
	service_request_names: list[str],
) -> list:
	"""Return the caller's Sales Orders that relate to the property."""
	return _get_vouchers(
		"Sales Order",
		SALES_ORDER_FIELDS,
		"transaction_date",
		customer_names,
		meter_reading_names,
		service_request_names,
	)


def get_sales_invoices(
	customer_names: list[str],
	meter_reading_names: list[str],
	service_request_names: list[str],
) -> list:
	"""Return the caller's Sales Invoices that relate to the property."""
	return _get_vouchers(
		"Sales Invoice",
		SALES_INVOICE_FIELDS,
		"posting_date",
		customer_names,
		meter_reading_names,
		service_request_names,
	)


def get_payment_entries(customer_names: list[str], voucher_names: list[str]) -> list:
	"""Return the caller's Payment Entries allocated against the given vouchers."""
	if not voucher_names:
		return []

	reference = DocType("Payment Entry Reference")
	payment_entry = DocType("Payment Entry")

	return (
		frappe.qb.from_(payment_entry)
		.join(reference)
		.on(reference.parent == payment_entry.name)
		.select(*[getattr(payment_entry, field) for field in PAYMENT_ENTRY_FIELDS])
		.distinct()
		.where(
			(payment_entry.party.isin(customer_names))
			& (payment_entry.docstatus != 2)
			& (reference.reference_name.isin(voucher_names))
		)
		.orderby(payment_entry.posting_date, order=Order.desc)
		.run(as_dict=True)
	)


def build_totals(sales_invoices: list, payment_entries: list) -> dict:
	"""Summarise invoiced, outstanding and paid amounts for a property."""
	submitted_invoices = [invoice for invoice in sales_invoices if invoice.docstatus == 1]
	invoiced = sum(invoice.grand_total or 0 for invoice in submitted_invoices)
	outstanding = sum(invoice.outstanding_amount or 0 for invoice in submitted_invoices)
	paid = sum(
		(entry.received_amount or entry.paid_amount or 0)
		for entry in payment_entries
		if entry.docstatus == 1
	)

	return {
		"invoiced": invoiced,
		"outstanding": outstanding,
		"paid": paid,
		"currency": submitted_invoices[0].currency if submitted_invoices else None,
	}


def _get_vouchers(
	doctype: str,
	fields: tuple,
	date_field: str,
	customer_names: list[str],
	meter_reading_names: list[str],
	service_request_names: list[str],
) -> list:
	"""Return Sales Orders/Invoices linked through meter readings or service requests."""
	voucher = DocType(doctype)
	parent_names = _get_parents_from_meter_readings(meter_reading_names, doctype)

	if parent_names:
		condition = voucher.name.isin(parent_names)
	elif service_request_names:
		condition = voucher.utility_service_request.isin(service_request_names)
	else:
		return []

	return (
		frappe.qb.from_(voucher)
		.select(*[getattr(voucher, field) for field in fields])
		.where(
			(voucher.customer.isin(customer_names))
			& (voucher.docstatus != 2)
			& condition
		)
		.orderby(getattr(voucher, date_field), order=Order.desc)
		.run(as_dict=True)
	)


def _get_parents_from_meter_readings(meter_reading_names: list[str], doctype: str) -> list:
	"""Return the voucher names of the given meter readings for ``doctype``."""
	if not meter_reading_names:
		return []

	parents: set[str] = set()
	for child_doctype, link_field in METER_READING_LINKS:
		if not child_doctype.startswith(doctype):
			continue

		child = DocType(child_doctype)
		rows = (
			frappe.qb.from_(child)
			.select(child.parent)
			.distinct()
			.where(getattr(child, link_field).isin(meter_reading_names))
			.run(as_dict=True)
		)
		parents.update(row.parent for row in rows)

	return list(parents)
