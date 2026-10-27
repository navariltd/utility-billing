"""Demo leases: service requests, property allocations and contracts."""

from typing import Any

import frappe
from frappe.utils import add_months, flt, getdate, today

from .bill_structures import get_random_bill_structure
from .constants import DEMO_COMPANY, demo_company_names
from .customers import demo_customer_ids, resolve_customer
from .pricing import load_rent_rates
from .utils import safe_load_json

SERVICE_REQUEST_SAVEPOINT = "demo_service_request"


def clear_existing_contracts() -> None:
	"""Cancel and delete the Contracts of the demo Customers."""
	demo_parties = demo_customer_ids()
	if not demo_parties:
		return

	demo_contracts = {
		contract.name: contract
		for contract in frappe.get_all(
			"Contract",
			filters={"party_name": ("in", demo_parties)},
			fields=["name", "docstatus", "party_name"],
		)
	}

	for contract_name, contract in demo_contracts.items():
		try:
			if contract.docstatus == 1:
				frappe.get_doc("Contract", contract_name).cancel()
			frappe.delete_doc("Contract", contract_name, force=True, ignore_permissions=True)
		except Exception:
			frappe.log_error(f"Failed to delete Contract {contract_name}", "Demo Contract Deletion")


def assign_properties_to_request(
	doc,
	requested_props: list[dict[str, Any]],
	service_start,
	service_end,
	is_signed: bool,
) -> None:
	"""Assign every requested property to the full lease period."""
	if not requested_props:
		return

	insurances = frappe.get_all("Insurance", pluck="name", order_by="name asc")

	for index, prop in enumerate(requested_props):
		insurance = insurances[index % len(insurances)] if insurances else None
		doc.append(
			"requested_properties",
			{
				"utility_property": prop.get("utility_property"),
				"insurance": insurance,
				"start_date": service_start,
				"end_date": service_end,
				"adjustment_rule": prop.get("adjustment_rule"),
				"status": "Occupied" if is_signed else "Reserved",
			},
		)

	if len(requested_props) == 1:
		doc.utility_property = requested_props[0].get("utility_property")


def append_property_service_items(doc) -> None:
	"""Add each requested property's rent service item to the request items."""
	from utility_billing.utility_billing.utils.service_item import ensure_service_item

	rent_rates = load_rent_rates()

	for row in doc.get("requested_properties") or []:
		if not row.utility_property:
			continue

		item_code = ensure_service_item(row.utility_property)
		if not item_code or any(item.item_code == item_code for item in doc.items):
			continue

		item = frappe.get_cached_doc("Item", item_code)
		rate = flt(rent_rates.get(row.utility_property))
		doc.append(
			"items",
			{
				"item_code": item_code,
				"item_name": item.item_name,
				"item_group": item.item_group,
				"uom": item.stock_uom,
				"stock_uom": item.stock_uom,
				"conversion_factor": 1,
				"qty": 1,
				"rate": rate,
				"amount": rate,
				"delivery_date": row.start_date,
			},
		)


def apply_contract_terms(doc, template_name: str) -> None:
	"""Copy contract terms from template."""
	if not template_name:
		return
	template_doc = frappe.get_doc("Contract Template", template_name)
	if template_doc and template_doc.contract_terms:
		doc.contract_terms = template_doc.contract_terms


def create_and_finalize_contract(service_request_name: str, is_signed: bool, properties: list) -> None:
	"""Create, submit, and optionally sign the associated contract."""
	from utility_billing.utility_billing.doctype.utility_service_request.utility_service_request import (
		create_contract,
	)

	contract_name = create_contract(service_request_name)
	contract = frappe.get_doc("Contract", contract_name)
	contract.save(ignore_permissions=True)
	contract.submit()

	status = "Occupied" if is_signed else "Reserved"
	for prop in properties:
		if prop.get("utility_property"):
			try:
				property_doc = frappe.get_doc("Utility Property", prop.get("utility_property"))
				property_doc.status = status
				property_doc.save(ignore_permissions=True)
			except Exception as e:
				frappe.log_error(f"Failed to update property status: {str(e)}")

	if is_signed:
		contract.is_signed = 1
		contract.save(ignore_permissions=True)


def insert_service_requests() -> list[str]:
	"""Insert the demo requests, their contracts and property allocations."""
	service_requests = safe_load_json("data/utility_service_request.json") or []
	names = []

	for request in service_requests:
		frappe.db.savepoint(SERVICE_REQUEST_SAVEPOINT)
		try:
			properties = request.get("requested_properties") or []
			if any(_already_leased(row.get("utility_property")) for row in properties):
				continue

			service_start = add_months(getdate(today()), int(request.get("start_offset_months") or 0))
			contract_length = request.get("contract_length_months", 12)
			service_end = add_months(service_start, contract_length)
			is_signed = bool(request.get("is_signed"))
			customer = resolve_customer(request.get("party_name"))
			if not customer:
				raise ValueError(f"Customer {request.get('party_name')} was not found.")

			doc = frappe.get_doc(
				{
					"doctype": "Utility Service Request",
					"request_type": request.get("request_type"),
					"service_request_from": "Customer",
					"party_name": customer.name,
					"customer": customer.name,
					"customer_name": customer.customer_name,
					"customer_group": request.get("customer_group"),
					"territory": customer.territory,
					"price_list": request.get("price_list"),
					"start_date": service_start,
					"end_date": service_end,
					"contract_length_months": contract_length,
					"contract_template": request.get("contract_template"),
					"utility_bill_structure": get_random_bill_structure(),
					"company": DEMO_COMPANY,
				}
			)

			assign_properties_to_request(doc, properties, service_start, service_end, is_signed)
			apply_contract_terms(doc, request.get("contract_template"))
			doc.insert(ignore_permissions=True)
			append_property_service_items(doc)
			doc.save(ignore_permissions=True)
			doc.submit()

			if properties:
				create_and_finalize_contract(doc.name, is_signed, properties)

			names.append(doc.name)
		except Exception as exc:
			frappe.db.rollback(save_point=SERVICE_REQUEST_SAVEPOINT)
			frappe.log_error(
				"insert_service_requests",
				f"Error creating service request for {request.get('party_name')}: {exc}",
			)

	return names


def _already_leased(property_name: str | None) -> bool:
	"""Return whether a submitted demo request already uses the property."""
	if not property_name:
		return False

	parents = frappe.get_all(
		"Contract Utility Property Item",
		filters={
			"parenttype": "Utility Service Request",
			"utility_property": property_name,
		},
		pluck="parent",
	)
	if not parents:
		return False

	companies = demo_company_names()
	if not companies:
		return False

	return bool(
		frappe.get_all(
			"Utility Service Request",
			filters={
				"name": ("in", parents),
				"company": ("in", companies),
				"docstatus": 1,
			},
			pluck="name",
			limit=1,
		)
	)


def clear_service_requests() -> None:
	"""Cancel and delete demo Utility Service Requests and their invoices."""
	companies = demo_company_names()
	if not companies:
		return

	demo_requests = frappe.get_all(
		"Utility Service Request",
		filters={"company": ("in", companies)},
		fields=["name", "docstatus"],
	)

	for request in demo_requests:
		invoices = frappe.get_all(
			"Sales Invoice",
			filters={"utility_service_request": request.name},
			fields=["name", "docstatus"],
		)

		for invoice in invoices:
			try:
				auto_repeats = frappe.get_all(
					"Auto Repeat",
					filters={
						"reference_doctype": "Sales Invoice",
						"reference_document": invoice.name,
					},
					pluck="name",
				)

				for auto_repeat in auto_repeats:
					auto_repeat_doc = frappe.get_doc("Auto Repeat", auto_repeat)
					if auto_repeat_doc.docstatus == 1:
						auto_repeat_doc.cancel()
					frappe.delete_doc(
						"Auto Repeat",
						auto_repeat,
						force=True,
						ignore_permissions=True,
					)

				if invoice.docstatus == 1:
					frappe.get_doc("Sales Invoice", invoice.name).cancel()

				frappe.delete_doc(
					"Sales Invoice",
					invoice.name,
					force=True,
					ignore_permissions=True,
				)
			except Exception:
				frappe.log_error(
					f"Failed to delete Sales Invoice {invoice.name}",
					"Demo Invoice Deletion",
				)

	for request in demo_requests:
		try:
			if request.docstatus == 1:
				frappe.get_doc("Utility Service Request", request.name).cancel()
			frappe.delete_doc(
				"Utility Service Request",
				request.name,
				force=True,
				ignore_permissions=True,
			)
		except Exception:
			frappe.log_error(
				f"Failed to delete Utility Service Request {request.name}",
				"Service Request Deletion Failed",
			)
