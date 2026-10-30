"""Selling rate of an item on a given date.

Rent and utility rates change over time: every price period is stored as its own
``Item Price`` record (see ``item_prices``), so the price of an invoice line
depends on the date its revenue belongs to. This module resolves the rate valid
on a date for an item, a customer and a price list, which is what the Sales
Invoice item grid uses when a Deferred Posting Date is set on a line.
"""

import frappe
from erpnext.stock.get_item_details import get_price_list_rate_for
from frappe.query_builder import Order
from frappe.query_builder.functions import IfNull
from frappe.utils import cint, flt

from utility_billing.utility_billing.utils import request_prices
from utility_billing.utility_billing.utils.price_list import resolve_price_list


def get_rate_for_date(
	item_code: str,
	posting_date: str,
	*,
	customer: str | None = None,
	price_list: str | None = None,
	uom: str | None = None,
	qty: float | None = None,
	conversion_factor: float = 1,
	plc_conversion_rate: float = 1,
	conversion_rate: float = 1,
	service_request: str | None = None,
) -> float | None:
	"""Return the selling rate of an item valid on a date.

	Customer specific prices take precedence over general ones and a UOM other
	than the one of the price is converted with the conversion factor of the
	line, matching how ERPNext prices a transaction.

	Args:
		item_code: Item being billed.
		posting_date: Date the rate has to be valid on.
		customer: Customer the rate is scoped to, if any.
		price_list: Price list the rate is read from. Defaults to the price list
			of the customer, or the one configured in Utility Billing Settings.
		uom: UOM of the invoice line. Defaults to the stock UOM of the item.
		qty: Quantity of the line, used for price list packing units.
		conversion_factor: Stock UOM to UOM conversion factor of the line.
		plc_conversion_rate: Price list currency to company currency rate.
		conversion_rate: Transaction currency to company currency rate.
		service_request: When given under the Item Price approach, only the
			prices this Utility Service Request owns are considered: its
			customer's prices of the item that start inside the lease window.
			Blank customer prices never apply. Ignored under Auto Repeat.

	Returns:
		The rate in the currency of the transaction, or None when no Item Price
		covers the item, the customer and the date.
	"""
	price_list = price_list or resolve_price_list(customer)
	if not (item_code and posting_date and price_list):
		return None

	stock_uom = frappe.get_cached_value("Item", item_code, "stock_uom")

	context = frappe._dict(
		{
			"price_list": price_list,
			"customer": customer,
			"uom": uom or stock_uom,
			"stock_uom": stock_uom,
			"transaction_date": posting_date,
			"qty": qty,
			"conversion_factor": flt(conversion_factor) or 1,
			"price_list_uom_dependant": cint(
				frappe.get_cached_value("Price List", price_list, "price_list_uom_dependant")
			),
		}
	)

	price_list_rate = (
		get_request_price(context, item_code, service_request)
		if service_request and request_prices.is_item_price_approach()
		else get_price_list_rate_for(context, item_code)
	)
	if price_list_rate is None:
		return None

	return flt(price_list_rate, 6) * flt(plc_conversion_rate, 6) / (flt(conversion_rate, 6) or 1)


def get_request_price(context: frappe._dict, item_code: str, service_request: str) -> float | None:
	"""Return the rate of the Item Price a request owns that is valid on the context date.

	Mirrors ERPNext's lookup (UOM match or blank, latest ``valid_from`` first and a
	UOM conversion when the price is not UOM dependant), restricted to one request:
	its customer and the lease window of the property the item bills.
	"""
	request = frappe.get_doc("Utility Service Request", service_request)
	property_name = next(
		(name for name, item in request_prices.property_service_items(request).items() if item == item_code),
		None,
	)
	start, end = request_prices.lease_window(request, property_name) if property_name else (None, None)
	if not (start and request.customer):
		return None

	ip = frappe.qb.DocType("Item Price")
	date = context.transaction_date
	query = (
		frappe.qb.from_(ip)
		.select(ip.price_list_rate, ip.uom)
		.where(ip.item_code == item_code)
		.where(ip.price_list == context.price_list)
		.where(ip.customer == request.customer)
		.where(ip.valid_from >= start)
		.where(IfNull(ip.uom, "").isin(["", context.uom]))
		.where(IfNull(ip.valid_from, "2000-01-01") <= date)
		.where(IfNull(ip.valid_upto, "2500-12-31") >= date)
		.orderby(ip.valid_from, order=Order.desc)
		.limit(1)
	)
	if end:
		query = query.where(ip.valid_from <= end)
	rows = query.run(as_dict=True)

	if not rows:
		return None

	price = rows[0]
	if price.uom == context.uom or context.price_list_uom_dependant:
		return price.price_list_rate

	return flt(price.price_list_rate * flt(context.conversion_factor))
