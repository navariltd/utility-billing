"""Rent Item Prices for the demo properties.

The demo follows the site's configured **Rent Billing Approach**:

* ``Item Price``: each leased property gets the full dated schedule produced
  from its lease period and ``Billing Adjustment Rule``.
* ``Auto Repeat``: each property gets a single open-ended base price, while the
  recurring increment itself is carried by the generated Auto Repeat.

Available units always receive a base price so the portal booking summary can
show a rent amount before a lease exists.
"""

from datetime import date

import frappe
from frappe.utils import flt, getdate, today

from utility_billing.utility_billing.utils.item_price_uom import resolve_uom
from utility_billing.utility_billing.utils.item_prices import (
	ScheduleLine,
	ScheduleOptions,
	build_increment_rule,
	create_item_prices,
	resolve_frequency,
)
from utility_billing.utility_billing.utils.price_list import resolve_price_list
from utility_billing.utility_billing.utils.service_item import ensure_service_item

from .constants import DEMO_COMPANY
from .utils import logger, safe_load_json

RENT_FILE = "data/property_rent.json"
PRICING_SAVEPOINT = "demo_rent_pricing"


def load_rent_rates() -> dict[str, float]:
	"""Return the monthly rent configured for every demo unit."""
	return {
		row["property_name"]: flt(row["monthly_rent"])
		for row in safe_load_json(RENT_FILE) or []
		if row.get("property_name")
	}


def create_demo_rent_item_prices(service_request_names: list[str]) -> None:
	"""Create rent Item Prices for demo properties.

	Args:
	    service_request_names: Demo requests used to resolve the lease period,
	        customer, price list and adjustment rule of each occupied unit.
	"""
	settings = frappe.get_cached_doc("Utility Billing Settings")
	approach = settings.rent_billing_approach or "Auto Repeat"
	leases = _lease_map(service_request_names)

	for property_name, base_rate in load_rent_rates().items():
		if not frappe.db.exists("Utility Property", property_name):
			continue

		property_doc = frappe.get_doc("Utility Property", property_name)
		if property_doc.is_group:
			continue

		item_code = ensure_service_item(property_name)
		if not item_code:
			continue

		frappe.db.savepoint(PRICING_SAVEPOINT)
		try:
			lease = leases.get(property_name)
			if approach == "Item Price" and lease:
				_create_schedule(settings, property_name, item_code, base_rate, lease)
			else:
				_create_base_price(settings, property_name, item_code, base_rate, lease)
		except Exception:
			frappe.db.rollback(save_point=PRICING_SAVEPOINT)
			logger.exception(f"Could not create demo rent prices for {property_name}")


def _lease_map(service_request_names: list[str]) -> dict[str, dict]:
	"""Return the lease details of every property in the demo requests."""
	leases = {}

	for name in service_request_names:
		request = frappe.get_doc("Utility Service Request", name)
		if request.company != DEMO_COMPANY:
			continue

		for row in request.get("requested_properties") or []:
			if not row.utility_property:
				continue

			leases[row.utility_property] = {
				"customer": request.customer,
				"price_list": request.price_list,
				"start_date": row.start_date or request.start_date,
				"end_date": row.end_date or request.end_date,
				"adjustment_rule": row.adjustment_rule,
			}

	return leases


def _create_schedule(settings, property_name: str, item_code: str, base_rate: float, lease: dict) -> None:
	"""Create the full dated Item Price schedule of one lease."""
	price_list = (
		lease.get("price_list") or resolve_price_list(lease.get("customer")) or settings.default_price_list
	)
	start_date = lease.get("start_date")
	if not (price_list and start_date):
		return

	rule = lease.get("adjustment_rule")
	options = ScheduleOptions(
		price_list=price_list,
		start_date=start_date,
		end_date=lease.get("end_date"),
		uom=resolve_uom(settings, [item_code]),
		frequency=resolve_frequency(rule),
		rule=build_increment_rule(rule),
	)
	line = ScheduleLine(
		item_code=item_code,
		customer=lease.get("customer"),
		base_rate=base_rate,
		utility_property=property_name,
	)

	result = create_item_prices(options, [line])
	logger.info(
		f"Rent schedule for {property_name}: {result['created_count']} created, {result['skipped']} skipped"
	)


def _create_base_price(
	settings, property_name: str, item_code: str, base_rate: float, lease: dict | None
) -> None:
	"""Create one open-ended base Item Price for a property."""
	customer = lease.get("customer") if lease else None
	price_list = (
		(lease.get("price_list") if lease else None)
		or resolve_price_list(customer)
		or settings.default_price_list
	)
	if not price_list:
		return

	valid_from = (lease or {}).get("start_date") or today()
	uom = resolve_uom(settings, [item_code])

	if _has_price_covering(item_code, price_list, uom, valid_from):
		return

	frappe.get_doc(
		{
			"doctype": "Item Price",
			"item_code": item_code,
			"price_list": price_list,
			"uom": uom,
			"customer": customer,
			"price_list_rate": base_rate,
			"valid_from": valid_from,
			"tariffs": [],
		}
	).insert(ignore_permissions=True)


def _has_price_covering(item_code: str, price_list: str, uom: str, valid_from: date | str) -> bool:
	"""Return whether a base Item Price already covers ``valid_from``."""
	valid_from = getdate(valid_from)

	prices = frappe.get_all(
		"Item Price",
		filters={
			"item_code": item_code,
			"price_list": price_list,
			"uom": uom,
			"valid_from": ("<=", valid_from),
		},
		fields=["valid_from", "valid_upto"],
	)

	return any(price.valid_upto is None or getdate(price.valid_upto) >= valid_from for price in prices)
