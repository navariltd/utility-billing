"""Whitelisted helpers of the Sales Invoice item grid.

The Sales Invoice form calls these to keep an invoice line in step with its
Deferred Posting Date and with the utility property its item belongs to.
"""

import frappe

from utility_billing.utility_billing.utils.item_price_scope import is_item_price_approach
from utility_billing.utility_billing.utils.item_rate import get_rate_for_date
from utility_billing.utility_billing.utils.service_item import (
	get_property_of_service_item,
	get_service_item_of_property,
)
from utility_billing.utility_billing.utils.utility_item_classifier import (
	get_request_lines,
	match_error_message,
	match_requests,
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


@frappe.whitelist()
def match_utility_service_requests(
	customer: str, item_codes: list | str, new_item_code: str | None = None
) -> dict:
	"""Return the Utility Service Requests able to govern an invoice's utility lines.

	Args:
		customer: Customer of the invoice.
		item_codes: Item codes on the invoice; non utility items are ignored.
		new_item_code: Item just added, named in a blocking message.

	Returns:
		``applies`` (False when the invoice has no utility item or rates are not
		billed by Item Price) and, when it applies, ``status``, ``candidates``,
		``missing`` and the blocking ``message`` if any.
	"""
	if not is_item_price_approach():
		return {"applies": False}

	frappe.has_permission("Utility Service Request", "read", throw=True)

	codes = frappe.parse_json(item_codes) if isinstance(item_codes, str) else item_codes
	match = match_requests(customer, codes)
	if not match.status:
		return {"applies": False}

	return {
		"applies": True,
		"status": match.status,
		"candidates": match.candidates,
		"missing": match.missing,
		"message": match_error_message(match, customer, new_item_code),
	}


@frappe.whitelist()
def get_utility_service_request_lines(utility_service_request: str) -> list[dict]:
	"""Return the governed utility lines of a Utility Service Request.

	Args:
		utility_service_request: ``Utility Service Request`` name.

	Returns:
		One entry per utility item with its ``role``, ``rate``, ``qty`` and ``uom``.
	"""
	if not is_item_price_approach():
		return []

	frappe.has_permission(
		"Utility Service Request", "read", doc=utility_service_request, throw=True
	)

	return list(get_request_lines(utility_service_request).values())
