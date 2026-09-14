"""Meter readings and service requests of a property, plus document orchestration.

This module collects everything a portal user is allowed to see about a property
they are linked to:

* ``Meter Reading`` rows recorded for the property (``Meter Reading.property``);
* ``Utility Service Request`` rows raised for the property, either naming it
  directly or listing it in ``requested_properties``;
* the billing vouchers and payments returned by
  :mod:`utility_billing.api.portal.property_vouchers`.

Every query is scoped to the caller's own Customers (``Customer.portal_users``)
**and** the requested property, so a user can only ever see their own documents.
Permissions are bypassed deliberately (``frappe.db.get_all`` / query builder)
because Website Users have no read access to these doctypes.
"""

import frappe
from frappe.query_builder import DocType

from utility_billing.api.portal.property_vouchers import (
	build_totals,
	get_payment_entries,
	get_sales_invoices,
	get_sales_orders,
)

METER_READING_FIELDS = ("name", "date", "customer", "company", "docstatus")

SERVICE_REQUEST_FIELDS = (
	"name",
	"date",
	"request_type",
	"request_status",
	"customer",
)


def get_property_documents(property_name: str, customer_names: list[str]) -> dict:
	"""Return the caller's documents that relate to ``property_name``.

	Args:
	    property_name: ``Utility Property`` name.
	    customer_names: Customers the caller is linked to (empty for guests).

	Returns:
	    Dict with ``meter_readings``, ``service_requests``, ``sales_invoices``,
	    ``sales_orders``, ``payment_entries`` and a ``totals`` summary.
	"""
	if not customer_names:
		return _empty_documents()

	meter_readings = _get_meter_readings(property_name, customer_names)
	service_requests = _get_service_requests(property_name, customer_names)
	meter_reading_names = [meter.name for meter in meter_readings]
	service_request_names = [request.name for request in service_requests]

	sales_orders = get_sales_orders(
		customer_names, meter_reading_names, service_request_names
	)
	sales_invoices = get_sales_invoices(
		customer_names, meter_reading_names, service_request_names
	)
	payment_entries = get_payment_entries(
		customer_names,
		[invoice.name for invoice in sales_invoices]
		+ [order.name for order in sales_orders],
	)

	return {
		"meter_readings": meter_readings,
		"service_requests": service_requests,
		"sales_invoices": sales_invoices,
		"sales_orders": sales_orders,
		"payment_entries": payment_entries,
		"totals": build_totals(sales_invoices, payment_entries),
	}


def _empty_documents() -> dict:
	"""Document payload for users without linked Customers (e.g. guests)."""
	return {
		"meter_readings": [],
		"service_requests": [],
		"sales_invoices": [],
		"sales_orders": [],
		"payment_entries": [],
		"totals": {"invoiced": 0, "outstanding": 0, "paid": 0, "currency": None},
	}


def _get_meter_readings(property_name: str, customer_names: list[str]) -> list:
	"""Return the meter readings of the property for the caller's customers."""
	return frappe.db.get_all(
		"Meter Reading",
		filters={
			"property": property_name,
			"customer": ("in", customer_names),
			"docstatus": ("!=", 2),
		},
		fields=list(METER_READING_FIELDS),
		order_by="date desc",
	)


def _get_service_requests(property_name: str, customer_names: list[str]) -> list:
	"""Return the service requests raised for the property by the caller's customers."""
	request = DocType("Utility Service Request")
	requested_property = DocType("Contract Utility Property Item")

	direct = _run_request_query(
		request, request.utility_property == property_name, customer_names
	)

	child_rows = (
		frappe.qb.from_(requested_property)
		.select(requested_property.parent)
		.distinct()
		.where(
			(requested_property.utility_property == property_name)
			& (requested_property.parenttype == "Utility Service Request")
		)
		.run(as_dict=True)
	)
	parent_names = {row.parent for row in child_rows} - {row.name for row in direct}

	if parent_names:
		direct = [
			*direct,
			*_run_request_query(
				request, request.name.isin(list(parent_names)), customer_names
			),
		]

	return sorted(direct, key=lambda row: row.get("date") or "", reverse=True)


def _run_request_query(request, property_condition, customer_names: list[str]) -> list:
	"""Run the service request query with the given property condition."""
	return (
		frappe.qb.from_(request)
		.select(*[getattr(request, field) for field in SERVICE_REQUEST_FIELDS])
		.where(
			property_condition
			& (request.customer.isin(customer_names))
			& (request.docstatus != 2)
		)
		.run(as_dict=True)
	)
