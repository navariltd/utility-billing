"""Requests, prices and unsaved invoices shared by the invoice line request tests.

Invoices are built in memory and governed by calling the hook functions, as in
``test_invoice_line_dimensions``, so no test needs the line field's column.
Everything runs inside the savepoint of ``lease_fixtures.SavepointMixin``.
"""

import frappe

from utility_billing.utility_billing.tests import factories
from utility_billing.utility_billing.tests import lease_fixtures as fx

P1 = "_Test Line USR P1"
P2 = "_Test Line USR P2"
ELECTRICITY = "_Test Line USR Electricity"
OTHER_ITEM = "_Test Line USR Other Item"
OTHER_CUSTOMER = "_Test Line USR Other Customer"


def setup_items() -> None:
	for name in (P1, P2):
		fx.lease_property(name)
	for code in (ELECTRICITY, OTHER_ITEM):
		factories.ensure_item(code)
	frappe.db.set_value("Item", ELECTRICITY, "is_utility_item", 1)
	frappe.db.set_value("Item", OTHER_ITEM, "is_utility_item", 0)
	factories.ensure_customer(OTHER_CUSTOMER)


def currency() -> str:
	return frappe.get_cached_value("Company", fx.company(), "default_currency")


def make_request(rows, start, end, secondary=(), customer=fx.CUSTOMER, submit=True):
	"""Insert a request leasing ``rows`` of ``(property, start, end)`` and listing ``secondary`` items.

	Args:
		secondary: ``(item_code, rate)`` pairs listed on the request without a property.
	"""
	factories.ensure_customer(customer)
	factories.ensure_price_list(fx.PRICE_LIST)
	frappe.db.set_value("Price List", fx.PRICE_LIST, "currency", currency())

	request = frappe.new_doc("Utility Service Request")
	request.update(
		{
			"service_request_from": "Customer",
			"party_name": customer,
			"customer": customer,
			"company": fx.company(),
			"price_list": fx.PRICE_LIST,
			"request_type": "Rent",
			"currency": currency(),
			"start_date": start,
			"end_date": end,
		}
	)
	for property_name, row_start, row_end in rows:
		request.append(
			"requested_properties",
			{
				"utility_property": property_name,
				"item_code": property_name,
				"start_date": row_start,
				"end_date": row_end,
				"is_active": 1,
				"rent_billing_approach": "Item Price",
			},
		)
		request.append("items", line(property_name, 1000))
	for item_code, rate in secondary:
		request.append("items", line(item_code, rate))
	request.flags.ignore_mandatory = True
	request.insert(ignore_permissions=True)
	if submit:
		request.submit()

	return request


def line(item_code, rate):
	return {"item_code": item_code, "item_name": item_code, "qty": 1, "rate": rate, "uom": "Nos", "conversion_factor": 1}


def make_price(item_code, rate, valid_from, valid_upto, customer=fx.CUSTOMER) -> None:
	frappe.get_doc(
		{
			"doctype": "Item Price",
			"item_code": item_code,
			"price_list": fx.PRICE_LIST,
			"customer": customer,
			"uom": "Nos",
			"price_list_rate": rate,
			"valid_from": valid_from,
			"valid_upto": valid_upto,
		}
	).insert(ignore_permissions=True)


def make_invoice(lines, posting_date, header=None, customer=fx.CUSTOMER, **values):
	"""Return an unsaved invoice billing ``lines``, each a dict of line values."""
	invoice = frappe.new_doc("Sales Invoice")
	invoice.update(
		{
			"customer": customer,
			"company": fx.company(),
			"posting_date": posting_date,
			"currency": currency(),
			"selling_price_list": fx.PRICE_LIST,
			"conversion_rate": 1,
			"plc_conversion_rate": 1,
			"utility_service_request": header,
			**values,
		}
	)
	for values_of_line in lines:
		invoice.append("items", {"qty": 1, "uom": "Nos", "conversion_factor": 1, **values_of_line})

	return invoice


def fingerprint(invoice) -> dict:
	"""Return what governance may change on an invoice, to compare with develop."""
	return {
		"header": invoice.get("utility_service_request"),
		"lines": [
			(
				row.item_code,
				row.get("utility_property"),
				row.get("utility_service_request"),
				row.get("rate"),
				row.get("price_list_rate"),
				row.get("meter_reading"),
			)
			for row in invoice.items
		],
	}
