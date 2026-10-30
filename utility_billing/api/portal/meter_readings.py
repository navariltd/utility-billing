"""Meter readings recorded for the caller's units.

The portal lists every non-cancelled ``Meter Reading`` billed to the caller's
Customers, together with the meter lines of each reading (previous reading,
current reading and consumption) and the amount billed for them. A single
reading is also returned in full, including its tariff block distribution.
Queries are scoped to the session user's Customers (``Customer.portal_users``);
framework permissions are bypassed deliberately because Website Users have no
read access to these doctypes.
"""

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import cint, flt

from utility_billing.api.portal.roles import get_portal_customers, require_authenticated_user

DEFAULT_LIMIT = 200

READING_FIELDS = (
	"name",
	"date",
	"customer",
	"customer_name",
	"property",
	"company",
	"currency",
	"price_list",
	"docstatus",
)

ITEM_FIELDS = (
	"name",
	"parent",
	"item_code",
	"item_name",
	"meter_number",
	"uom",
	"previous_reading",
	"current_reading",
	"consumption",
)

RATE_FIELDS = (
	"parent",
	"meter_reading_item",
	"item_code",
	"block",
	"qty",
	"rate",
	"amount",
)

PROPERTY_FIELDS = ("name", "property_name", "unit_number", "house_no", "plot_no")

# Most specific identifier first: a tenant recognises their unit number, not the
# internal Utility Property name.
PROPERTY_LABEL_FIELDS = ("unit_number", "house_no", "plot_no", "property_name")


@frappe.whitelist()
def get_customer_meter_readings(limit: int = DEFAULT_LIMIT) -> dict:
	"""Return the meter readings recorded for the caller's Customers.

	Args:
		limit: Maximum number of readings returned, newest first.

	Returns:
		Dict with ``customer``, ``customers``, ``meter_readings`` (each with its
		``items``, ``total_consumption`` and ``total_amount``), the
		``properties`` they belong to and a ``totals`` summary.
	"""
	require_authenticated_user()
	customers = get_portal_customers()
	if not customers:
		return _payload(None, [], [], [])

	customer_names = [customer["name"] for customer in customers]
	readings = frappe.db.get_all(
		"Meter Reading",
		filters={"customer": ("in", customer_names), "docstatus": ("!=", 2)},
		fields=list(READING_FIELDS),
		order_by="date desc, name desc",
		limit=cint(limit) or DEFAULT_LIMIT,
	)
	if not readings:
		return _payload(customer_names[0], customers, [], [])

	_attach_items(readings, _get_items([reading.name for reading in readings]))
	_attach_amounts(readings, _get_rates([reading.name for reading in readings]))
	properties = _get_properties(readings)
	_attach_property_labels(readings, properties)

	return _payload(customer_names[0], customers, readings, list(properties.values()))


@frappe.whitelist()
def get_customer_meter_reading(name: str) -> dict:
	"""Return one meter reading of the caller's Customers in full.

	Args:
		name: ``Meter Reading`` name.

	Returns:
		The reading with its meter lines, tariff ``rates`` (the block
		distribution) and a ``totals`` summary.

	Raises:
		frappe.DoesNotExistError: When the reading does not belong to any of
		the caller's Customers.
	"""
	require_authenticated_user()
	reading = _get_reading(name, [customer["name"] for customer in get_portal_customers()])
	if not reading:
		frappe.throw(_("Meter Reading {0} was not found.").format(name), frappe.DoesNotExistError)

	_attach_items([reading], _get_items([reading.name]))
	_attach_property_labels([reading], _get_properties([reading]))

	rates = _get_rates([reading.name])
	_attach_amounts([reading], rates)
	_label_rates(rates, reading["items"])
	reading["rates"] = rates
	reading["totals"] = {
		"consumption": reading["total_consumption"],
		"amount": reading["total_amount"],
		"blocks": len(rates),
	}

	return reading


def _get_reading(name: str, customer_names: list[str]):
	"""Return one non-cancelled reading of ``customer_names``, or ``None``."""
	if not customer_names:
		return None

	return frappe.db.get_value(
		"Meter Reading",
		{"name": name, "customer": ("in", customer_names), "docstatus": ("!=", 2)},
		list(READING_FIELDS),
		as_dict=True,
	)


def _payload(customer: str | None, customers: list, readings: list, properties: list) -> dict:
	"""Assemble the response payload, including its totals."""
	return {
		"customer": customer,
		"customers": customers,
		"meter_readings": readings,
		"properties": properties,
		"totals": {
			"readings": len(readings),
			"consumption": sum(flt(reading["total_consumption"]) for reading in readings),
			"amount": sum(flt(reading.get("total_amount")) for reading in readings),
			"currency": readings[0].get("currency") if readings else None,
			"latest_date": readings[0]["date"] if readings else None,
		},
	}


def _get_items(reading_names: list[str]) -> list:
	"""Return the meter lines of ``reading_names`` in a single query."""
	return frappe.db.get_all(
		"Meter Reading Item",
		filters={"parent": ("in", reading_names), "parenttype": "Meter Reading"},
		fields=list(ITEM_FIELDS),
		order_by="idx asc",
	)


def _get_rates(reading_names: list[str]) -> list:
	"""Return the tariff block rows of ``reading_names`` in a single query."""
	return frappe.db.get_all(
		"Meter Reading Tariff Rate",
		filters={"parent": ("in", reading_names), "parenttype": "Meter Reading"},
		fields=list(RATE_FIELDS),
		order_by="idx asc",
	)


def _get_properties(readings: list) -> dict:
	"""Return the ``Utility Property`` rows behind the readings, keyed by name."""
	names = sorted({reading.property for reading in readings if reading.property})
	if not names:
		return {}

	return {
		row.name: row
		for row in frappe.db.get_all(
			"Utility Property", filters={"name": ("in", names)}, fields=list(PROPERTY_FIELDS)
		)
	}


def _attach_items(readings: list, items: list) -> None:
	"""Group meter lines by reading and total their consumption."""
	grouped = defaultdict(list)
	for item in items:
		item["consumption"] = flt(item.get("consumption")) or (
			flt(item.get("current_reading")) - flt(item.get("previous_reading"))
		)
		grouped[item.parent].append(item)

	for reading in readings:
		reading["items"] = grouped[reading.name]
		reading["total_consumption"] = sum(flt(item["consumption"]) for item in reading["items"])


def _attach_amounts(readings: list, rates: list) -> None:
	"""Add the amount billed for each reading, summed from its tariff block rows."""
	amounts = defaultdict(float)
	for rate in rates:
		amounts[rate.parent] += flt(rate.get("amount"))

	for reading in readings:
		reading["total_amount"] = amounts.get(reading.name, 0.0)


def _label_rates(rates: list, items: list) -> None:
	"""Add the meter line details the portal shows next to each block row."""
	lines = {item.get("name"): item for item in items}
	for rate in rates:
		line = lines.get(rate.get("meter_reading_item")) or {}
		rate["item_name"] = line.get("item_name") or rate.get("item_code")
		rate["meter_number"] = line.get("meter_number")
		rate["uom"] = line.get("uom")


def _attach_property_labels(readings: list, properties: dict) -> None:
	"""Add the tenant-facing label of each reading's unit."""
	for reading in readings:
		reading["property_label"] = _property_label(properties.get(reading.property))


def _property_label(property_row) -> str | None:
	"""Return the most specific label of a unit, falling back to its name."""
	if not property_row:
		return None

	for field in PROPERTY_LABEL_FIELDS:
		if property_row.get(field):
			return property_row.get(field)

	return property_row.get("name")
