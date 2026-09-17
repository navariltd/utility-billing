"""Whitelisted helpers of the Sales Invoice item grid.

The Sales Invoice form calls these to keep an invoice line in step with its
Deferred Posting Date and with the utility property its item belongs to.
"""

import frappe

from utility_billing.utility_billing.utils.item_rate import get_rate_for_date
from utility_billing.utility_billing.utils.service_item import (
	get_property_of_service_item,
	get_service_item_of_property,
)


@frappe.whitelist()
def get_line_rate(
	item_code: str,
	posting_date: str,
	customer: str | None = None,
	price_list: str | None = None,
	uom: str | None = None,
	qty: float | None = None,
	conversion_factor: float | None = None,
	plc_conversion_rate: float | None = None,
	conversion_rate: float | None = None,
) -> float | None:
	"""Return the rate of an item valid on a date.

	Used when the revenue of an invoice line is deferred: the line has to be
	billed at the rate that is valid on its Deferred Posting Date.

	Args:
		item_code: Item of the invoice line.
		posting_date: Date the rate has to be valid on.
		customer: Customer of the invoice, if any.
		price_list: Price list of the invoice, if any.
		uom: UOM of the invoice line, if any.
		qty: Quantity of the invoice line, if any.
		conversion_factor: Stock UOM to UOM conversion factor of the line.
		plc_conversion_rate: Price list currency to company currency rate.
		conversion_rate: Transaction currency to company currency rate.

	Returns:
		The rate in the currency of the transaction, or None when no Item Price
		covers the item, the customer and the date.
	"""
	return get_rate_for_date(
		item_code,
		posting_date,
		customer=customer,
		price_list=price_list,
		uom=uom,
		qty=qty,
		conversion_factor=conversion_factor or 1,
		plc_conversion_rate=plc_conversion_rate or 1,
		conversion_rate=conversion_rate or 1,
	)


@frappe.whitelist()
def get_line_utility_property(item_code: str) -> str | None:
	"""Return the utility property billed through an item.

	Args:
		item_code: Item of the invoice line.

	Returns:
		The ``Utility Property`` name, or None when the item is not the service
		item of a property or the property is not readable by the user.
	"""
	if not frappe.has_permission("Utility Property", "read"):
		return None

	return get_property_of_service_item(item_code)


@frappe.whitelist()
def get_line_item(utility_property: str) -> str | None:
	"""Return the service item to bill for a utility property.

	Args:
		utility_property: ``Utility Property`` name.

	Returns:
		The service item code, or None when the property has no service item and
		auto creation is disabled, or the property is not readable by the user.
	"""
	if not frappe.has_permission("Utility Property", "read"):
		return None

	return get_service_item_of_property(utility_property)
