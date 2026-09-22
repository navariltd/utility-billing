"""Properties linked to the signed in tenant.

A tenant reaches the portal through a standard ERPNext Customer: the user is
listed in ``Customer.portal_users`` and the tenancy is a ``Contract`` whose
``party_type`` is ``Customer`` and ``party_name`` is that Customer. Each
property of the tenancy lives in the ``Contract.properties`` child table
(``Contract Utility Property Item``) where ``is_active`` marks live allocations.

Allocations are classified as:

* ``Active``   – active allocation on a signed contract.
* ``Reserved`` – active allocation on a contract that is not signed yet.
* ``History``  – allocation that was deactivated or whose end date has passed.
"""

from frappe.query_builder import DocType
from frappe.utils import cint, getdate, today

import frappe

from utility_billing.api.portal.roles import get_linked_customers, require_authenticated_user

ACTIVE = "Active"
RESERVED = "Reserved"
HISTORY = "History"

CONTRACT_FIELDS = ("name", "party_name", "is_signed", "status", "start_date", "end_date")

CONTRACT_ITEM_FIELDS = (
	"parent",
	"utility_property",
	"start_date",
	"end_date",
	"is_active",
	"contract_length_months",
	"insurance",
)

PROPERTY_FIELDS = (
	"name",
	"property_name",
	"utility_category",
	"company",
	"status",
	"location",
	"territory",
	"house_no",
	"plot_no",
	"unit_number",
	"unit_type",
	"bedrooms",
	"bathrooms",
	"unit_size",
	"floor_level",
	"cover_image",
	"parent_utility_property",
)


def classify_lease_item(
	is_active: int | bool,
	end_date: str | None,
	contract_is_signed: int | bool,
	reference_date: str | None = None,
) -> str:
	"""Classify a single contract property allocation for the portal.

	Args:
	    is_active: ``Contract Utility Property Item.is_active``.
	    end_date: End date of the allocation, if any.
	    contract_is_signed: ``Contract.is_signed`` of the parent contract.
	    reference_date: Date used to detect expired allocations (defaults to today).

	Returns:
	    One of ``Active``, ``Reserved`` or ``History``.
	"""
	if not cint(is_active):
		return HISTORY

	reference_date = getdate(reference_date or today())
	if end_date and getdate(end_date) < reference_date:
		return HISTORY

	if not cint(contract_is_signed):
		return RESERVED

	return ACTIVE


def get_tenant_properties(user: str | None = None) -> dict:
	"""Return the current and historical properties of the tenant ``user``.

	Args:
	    user: User to inspect. Defaults to the current session user.

	Returns:
	    Dict with ``customer``, ``current`` (Active/Reserved) and ``history`` rows.
	"""
	customers = get_linked_customers(user)
	if not customers:
		return {"customer": None, "current": [], "history": []}

	contracts = _get_contracts([customer["name"] for customer in customers])
	if not contracts:
		return {"customer": customers[0]["name"], "current": [], "history": []}

	items = _get_contract_items([contract.name for contract in contracts])
	properties = _get_properties([item.utility_property for item in items if item.utility_property])
	contract_map = {contract.name: contract for contract in contracts}

	rows = []
	for item in items:
		contract = contract_map.get(item.parent)
		property_doc = properties.get(item.utility_property)
		if not contract or not property_doc:
			continue

		rows.append(_build_row(contract, item, property_doc))

	current = [row for row in rows if row["state"] != HISTORY]
	history = [row for row in rows if row["state"] == HISTORY]

	current.sort(key=lambda row: row.get("start_date") or "", reverse=True)
	history.sort(key=lambda row: row.get("end_date") or "", reverse=True)

	return {"customer": customers[0]["name"], "current": current, "history": history}


@frappe.whitelist()
def get_my_properties() -> dict:
	"""Return the properties linked to the session tenant.

	Returns:
	    The payload produced by :func:`get_tenant_properties`.

	Raises:
	    frappe.PermissionError: When the session user is anonymous.
	"""
	require_authenticated_user()
	return get_tenant_properties(frappe.session.user)


def _get_contracts(customer_names: list[str]) -> list:
	"""Return the contracts (drafts included, cancelled excluded) of the customers."""
	contract = DocType("Contract")

	return (
		frappe.qb.from_(contract)
		.select(*[getattr(contract, field) for field in CONTRACT_FIELDS])
		.where(
			(contract.party_type == "Customer")
			& (contract.party_name.isin(customer_names))
			& (contract.docstatus != 2)
		)
		.run(as_dict=True)
	)


def _get_contract_items(contract_names: list[str]) -> list:
	"""Return the property allocations of the given contracts."""
	item = DocType("Contract Utility Property Item")

	return (
		frappe.qb.from_(item)
		.select(*[getattr(item, field) for field in CONTRACT_ITEM_FIELDS])
		.where(item.parent.isin(contract_names))
		.run(as_dict=True)
	)


def _get_properties(property_names: list[str]) -> dict:
	"""Return a ``{property: details}`` map for the given property names."""
	if not property_names:
		return {}

	# `frappe.db.get_all` is used because Website Users have no permission on
	# Utility Property; the input is already limited to properties allocated to
	# the caller's own contracts.
	properties = frappe.db.get_all(
		"Utility Property",
		filters={"name": ("in", list({name for name in property_names}))},
		fields=list(PROPERTY_FIELDS),
	)

	return {property_doc.name: property_doc for property_doc in properties}


def _build_row(contract, item, property_doc) -> dict:
	"""Build a single portal row from a contract, its allocation and the property."""
	return {
		"utility_property": property_doc.name,
		"property_name": property_doc.property_name or property_doc.name,
		"utility_category": property_doc.utility_category,
		"company": property_doc.company,
		"location": property_doc.location,
		"territory": property_doc.territory,
		"house_no": property_doc.house_no,
		"plot_no": property_doc.plot_no,
		"unit_number": property_doc.unit_number,
		"unit_type": property_doc.unit_type,
		"bedrooms": property_doc.bedrooms,
		"bathrooms": property_doc.bathrooms,
		"unit_size": property_doc.unit_size,
		"floor_level": property_doc.floor_level,
		"cover_image": property_doc.cover_image,
		"parent_utility_property": property_doc.parent_utility_property,
		"state": classify_lease_item(item.is_active, item.end_date, contract.is_signed),
		"contract": contract.name,
		"contract_status": contract.status,
		"is_signed": cint(contract.is_signed),
		"start_date": item.start_date or contract.start_date,
		"end_date": item.end_date or contract.end_date,
		"contract_length_months": item.contract_length_months,
		"insurance": item.insurance,
	}
