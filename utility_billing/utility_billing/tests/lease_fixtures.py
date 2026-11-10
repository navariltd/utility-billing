"""Leases, Contracts and settings shared by the Contract and lease end tests.

Every test using these runs inside a savepoint rolled back in tearDown, so the
records never outlive the test. Utility Billing Settings are cached outside the
transaction, so the cache is cleared after each change and after the rollback.
"""

from contextlib import contextmanager
from unittest.mock import patch

import frappe

from utility_billing.utility_billing.doctype.utility_service_request.utility_service_request import (
	create_contract,
)
from utility_billing.utility_billing.tests import factories

SETTINGS = "Utility Billing Settings"
CUSTOMER = "_Test Lease Contract Customer"
PRICE_LIST = "_Test Lease Contract Price List"


def company() -> str:
	return frappe.db.get_value("Company", {}, "name")


def set_settings(**values) -> None:
	"""Write Utility Billing Settings and drop their cached copy."""
	frappe.db.set_single_value(SETTINGS, values)
	frappe.clear_cache(doctype=SETTINGS)


def use_approach(approach: str, require_contract: int = 0, require_signed: int = 1) -> None:
	set_settings(
		rent_billing_approach=approach,
		require_contract_before_sales_invoice_creation=require_contract,
		require_signed_contract=require_signed,
	)


def lease_property(name: str) -> str:
	"""Return an Available property owning a service item named after it."""
	factories.ensure_item(name)
	factories.ensure_property(name, service_item=name)
	frappe.db.set_value("Utility Property", name, "status", "Available")

	return name


def make_request(rows, start: str, end: str | None, submit: bool = True, billing: bool = False):
	"""Insert a Utility Service Request leasing ``rows`` of ``(property, start, end)``.

	Args:
		rows: Property rows, each ``(property, start, end)``.
		start: Request start date.
		end: Request end date.
		submit: Whether to submit the request.
		billing: Whether the rows are billed by the daily Item Price job on
			the first day of each month.
	"""
	factories.ensure_customer(CUSTOMER)
	factories.ensure_price_list(PRICE_LIST)
	# In the company's currency, so billing needs no exchange rate
	currency = frappe.get_cached_value("Company", company(), "default_currency")
	frappe.db.set_value("Price List", PRICE_LIST, "currency", currency)

	request = frappe.new_doc("Utility Service Request")
	request.service_request_from = "Customer"
	request.party_name = CUSTOMER
	request.customer = CUSTOMER
	request.company = company()
	request.price_list = PRICE_LIST
	request.request_type = "Rent"
	request.currency = currency
	request.start_date = start
	request.end_date = end
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
				"enable_auto_billing": 1 if billing else 0,
				"billing_date_type": "First Day of Month" if billing else None,
			},
		)
		request.append(
			"items",
			{
				"item_code": property_name,
				"item_name": property_name,
				"utility_property": property_name,
				"qty": 1,
				"rate": 1000,
				"uom": "Nos",
				"conversion_factor": 1,
			},
		)
	request.flags.ignore_mandatory = True
	request.insert(ignore_permissions=True)
	if submit:
		request.submit()

	return request


def make_contract(service_request: str, signed: bool = True, submit: bool = True):
	"""Make the request's Contract the way the form does, then sign and submit it."""
	contract = frappe.get_doc("Contract", create_contract(service_request))
	contract.contract_terms = contract.contract_terms or "Terms"
	contract.is_signed = 1 if signed else 0
	contract.save(ignore_permissions=True)
	if submit:
		contract.submit()

	return contract


def release_rows(contract, *indexes, released_on=None) -> None:
	"""Untick the given property rows of a submitted Contract and save it.

	Args:
		released_on: Released On of the rows; left blank, the save fills it.
	"""
	contract.reload()
	for index in indexes:
		contract.properties[index].is_active = 0
		if released_on:
			contract.properties[index].released_on = released_on
	contract.save(ignore_permissions=True)
	contract.reload()


def property_status(name: str) -> str:
	return frappe.db.get_value("Utility Property", name, "status")


def contract_status(name: str) -> str:
	return frappe.db.get_value("Contract", name, "status")


@contextmanager
def no_commit():
	"""Keep code that commits (job runner, job hooks) inside the test's savepoint."""
	with patch.object(frappe.db, "commit"):
		yield


class SavepointMixin:
	"""Run each test in a savepoint and restore the settings cache afterwards."""

	savepoint = "lease_contract_test"

	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		frappe.db.savepoint(self.savepoint)

	def tearDown(self):
		frappe.db.rollback(save_point=self.savepoint)
		frappe.clear_cache(doctype=SETTINGS)
		super().tearDown()
