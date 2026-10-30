import json
import os
from typing import Any, Callable

import frappe
from erpnext.setup.demo import create_transaction_deletion_record, delete_company

from .billing import clear_meter_readings, delete_sales_orders, insert_meter_readings
from .cleanup import (
	delete_demo_auto_repeats,
	delete_demo_property_item_prices,
	delete_demo_property_service_items,
)
from .company import create_sample_company
from .config import configure_demo_settings, ensure_demo_price_lists
from .constants import demo_company_names
from .fiscal import ensure_current_fiscal_year, reset_fiscal_year_cache
from .issues import clear_demo_support_issues, create_demo_support_issues
from .portal_users import create_portal_users, delete_demo_portal_users
from .pricing import create_demo_rent_item_prices
from .property_setup import delete_assets
from .service_request import (
	clear_bill_structures,
	clear_existing_contracts,
	clear_service_requests,
	insert_bill_structures,
	insert_service_requests,
)
from .transactions import create_demo_transactions
from .utils import apply_demo_flags, logger


def _company_has_transactions(company: str) -> bool:
	"""Return whether a demo company owns any accounting or operational documents."""
	doctypes = (
		"GL Entry",
		"Sales Invoice",
		"Sales Order",
		"Payment Entry",
		"Journal Entry",
		"Meter Reading",
		"Asset",
	)
	return any(frappe.db.exists(doctype, {"company": company}) for doctype in doctypes)


def _delete_company_child_rows(companies: list[str]) -> None:
	"""Delete company-specific child rows that standard company deletion ignores.

	Some installed apps (for example HRMS Expense Claim Accounts) store a company
	link in a child table whose parent has no company field. ERPNext's transaction
	deletion record cannot remove those rows, so they block company deletion.
	"""
	child_doctypes = frappe.get_all(
		"DocField",
		filters={"fieldtype": "Link", "options": "Company"},
		pluck="parent",
		distinct=True,
	)
	for doctype in child_doctypes:
		meta = frappe.get_meta(doctype)
		if meta.istable and meta.has_field("company") and frappe.db.has_column(doctype, "company"):
			frappe.db.delete(doctype, {"company": ("in", companies)})


def _savepoint_name(label: str) -> str:
	"""Return a SQL-safe savepoint name for a demo step label."""
	return "demo_" + "".join(char if char.isalnum() else "_" for char in label.lower())[:40]


def _run_step(label: str, func: Callable[[], Any], failures: list[str]) -> Any:
	"""Run one demo step in its own savepoint.

	Demo generation and deletion are best effort: a failing step is rolled back
	and reported instead of aborting every other step.
	"""
	save_point = _savepoint_name(label)
	frappe.db.savepoint(save_point)
	try:
		return func()
	except Exception:
		frappe.db.rollback(save_point=save_point)
		frappe.clear_messages()
		failures.append(label)
		logger.exception(f"Demo step failed: {label}")
		return None


def _report(message: str, failures: list[str], title: str) -> None:
	"""Show the outcome of a demo run and warn about the steps that failed."""
	if failures:
		detail = f"{title}. Steps that failed: {', '.join(failures)}."
		frappe.msgprint(detail, indicator="orange", title=title)
		logger.warning(detail)
	else:
		frappe.msgprint(message)
		logger.info(message)


def run_demo_setup() -> None:
	"""Run the complete demo setup process."""
	logger.info("Starting demo setup...")
	failures: list[str] = []

	try:
		frappe.db.begin()

		_run_step("company", create_sample_company, failures)
		reset_fiscal_year_cache()
		_run_step("fiscal year", ensure_current_fiscal_year, failures)
		_run_step("price lists", ensure_demo_price_lists, failures)
		_run_step("masters", process_masters, failures)
		_run_step("settings", configure_demo_settings, failures)
		_run_step("portal users", create_portal_users, failures)
		_run_step("bill structures", insert_bill_structures, failures)
		service_requests = _run_step("service requests", insert_service_requests, failures) or []
		_run_step("rent prices", lambda: create_demo_rent_item_prices(service_requests), failures)
		_run_step("meter readings", insert_meter_readings, failures)
		_run_step("transactions", lambda: create_demo_transactions(service_requests), failures)
		_run_step("support tickets", create_demo_support_issues, failures)

		frappe.db.commit()
		_report("Demo setup completed successfully.", failures, "Demo data partially generated")
	except Exception as e:
		frappe.db.rollback()
		error_msg = f"Demo setup failed: {str(e)}"
		frappe.msgprint(error_msg, indicator="red")
		logger.exception(error_msg)
		raise


def _company_transactions_deleted(companies: list[str], failures: list[str]) -> None:
	"""Hand every demo company's vouchers to ERPNext's deletion record first.

	``Transaction Deletion Record`` rolls back its own failed deletion tasks,
	so each record runs in a committed transaction of its own instead of
	sharing the transaction of the remaining demo cleanup.
	"""
	for company in companies:
		if not _company_has_transactions(company):
			continue

		try:
			create_transaction_deletion_record(company)
		except Exception:
			frappe.db.rollback()
			failures.append(f"transactions of {company}")
			logger.exception(f"ERPNext transaction deletion failed for {company}")

		frappe.db.commit()


def _delete_deletion_records(companies: list[str]) -> None:
	"""Cancel and delete the Transaction Deletion Records of the demo companies.

	The records are submitted by ERPNext before it starts the deletion tasks, and
	submitted documents cannot be deleted straight away, so each record is
	cancelled first.
	"""
	names = frappe.get_all(
		"Transaction Deletion Record",
		filters={"company": ("in", companies)},
		pluck="name",
	)

	for name in names:
		doc = frappe.get_doc("Transaction Deletion Record", name)
		if doc.docstatus == 1:
			apply_demo_flags(doc).cancel()
		frappe.delete_doc("Transaction Deletion Record", name, force=True, ignore_permissions=True)


def delete_demo_data() -> list[str]:
	"""Delete all demo data created by the setup process.

	ERPNext's transaction deletion runs first, then the demo specific records
	(service requests, meter readings, prices, portal users and masters) are
	cleared. Every step is best effort, so one problematic document does not
	block the cleanup of the rest.

	Returns:
	    The labels of the steps that could not be completed.
	"""
	logger.info("Starting demo data deletion...")
	failures: list[str] = []
	companies = demo_company_names()

	_run_step("auto repeats", delete_demo_auto_repeats, failures)
	frappe.db.commit()

	_company_transactions_deleted(companies, failures)

	try:
		frappe.db.begin()

		_run_step("sales orders", delete_sales_orders, failures)
		_run_step("meter readings", clear_meter_readings, failures)
		_run_step("contracts", clear_existing_contracts, failures)
		_run_step("service requests", clear_service_requests, failures)
		_run_step("bill structures", clear_bill_structures, failures)
		_run_step("support tickets", clear_demo_support_issues, failures)
		_run_step("rent item prices", delete_demo_property_item_prices, failures)
		_run_step("portal users", delete_demo_portal_users, failures)
		_run_step("assets", lambda: delete_assets(companies), failures)
		_run_step("masters", process_masters_deletion, failures)
		_run_step("service items", delete_demo_property_service_items, failures)
		_run_step("company child rows", lambda: _delete_company_child_rows(companies), failures)
		_run_step(
			"transaction deletion records", lambda: _delete_deletion_records(companies), failures
		)
		for company in companies:
			_run_step(f"company {company}", lambda company=company: delete_company(company), failures)

		frappe.db.commit()
	except Exception as e:
		frappe.db.rollback()
		error_msg = f"Demo data deletion failed: {str(e)}"
		frappe.msgprint(error_msg, indicator="red")
		logger.exception(error_msg)
		raise

	_report("Demo data deletion completed successfully.", failures, "Demo data partially deleted")
	return failures


def process_masters() -> None:
	"""Process and create master data records from JSON files."""
	try:
		for doctype in frappe.get_hooks("utility_demo_master_doctypes"):
			try:
				data = read_data_file_using_hooks(doctype)
				if data:
					for item in json.loads(data):
						create_demo_record(item)
			except Exception as e:
				error_msg = f"Failed to process master doctype {doctype}: {str(e)}"
				frappe.msgprint(error_msg, indicator="orange")
				logger.error(error_msg)
	except Exception as e:
		error_msg = f"Failed to process masters: {str(e)}"
		frappe.msgprint(error_msg, indicator="red")
		logger.error(error_msg)
		raise


def create_demo_record(item: dict[str, Any]) -> None:
	"""Create a single demo record, bypassing validation, permissions and links.

	Args:
	    item: Dictionary containing the record data to be inserted
	"""
	doctype = item.get("doctype")
	if not doctype:
		frappe.log_error("Demo Setup Error", f"Missing doctype in item: {item}")
		return

	if doctype == "Item Price" and item.get("item_code"):
		stock_uom = frappe.db.get_value("Item", item["item_code"], "stock_uom")
		if stock_uom:
			item["uom"] = stock_uom

	filters: dict[str, str | int | float | bool] = {
		field: value
		for field, value in item.items()
		if field != "doctype" and isinstance(value, (str, int, float, bool))
	}

	if filters and frappe.db.exists(doctype, filters):
		frappe.logger().debug(f"Record already exists for {doctype} with filters {filters}")
		return

	save_point = _savepoint_name(f"master_{doctype}")
	frappe.db.savepoint(save_point)
	try:
		_insert_demo_record(item)
	except frappe.exceptions.DuplicateEntryError:
		frappe.db.rollback(save_point=save_point)
		frappe.logger().debug(f"Duplicate record for {doctype}, skipping")
	except Exception:
		# A stray validation (mandatory field, tree parent, link check) should
		# not block the demo: retry once with validation switched off.
		frappe.db.rollback(save_point=save_point)
		try:
			_insert_demo_record(item, ignore_validate=True)
			frappe.logger().warning(f"Created {doctype} record while bypassing validation")
		except Exception as e:
			frappe.db.rollback(save_point=save_point)
			frappe.log_error(
				"Demo Setup Error", f"Failed to create demo record for {doctype}: {str(e)}"
			)


def _insert_demo_record(item: dict[str, Any], *, ignore_validate: bool = False) -> None:
	"""Insert a demo record with every bypass flag the demo setup needs."""
	doc = frappe.get_doc(item)
	doc.flags.ignore_permissions = True
	doc.flags.ignore_mandatory = True
	doc.flags.ignore_links = True
	doc.flags.ignore_validate = ignore_validate
	doc.insert()


def read_data_file_using_hooks(doctype: str) -> str:
	"""Read JSON data file for a specific doctype.

	Args:
	    doctype: The doctype name to read data for

	Returns:
	    The contents of the JSON file as a string
	"""
	path = os.path.join(os.path.dirname(__file__), "data")
	with open(os.path.join(path, f"{doctype}.json")) as f:
		data = f.read()

	return data


def process_masters_deletion() -> None:
	"""Delete all master data records created during demo setup."""
	try:
		# Process doctypes in reverse order to handle dependencies
		for doctype in reversed(frappe.get_hooks("utility_demo_master_doctypes")):
			save_point = _savepoint_name(f"delete_masters_{doctype}")
			frappe.db.savepoint(save_point)
			try:
				data = read_data_file_using_hooks(doctype)
				if data:
					for item in reversed(json.loads(data)):
						delete_demo_record(item)
			except Exception as e:
				frappe.db.rollback(save_point=save_point)
				frappe.log_error(
					"Demo Deletion Error", f"Failed to process deletion for doctype {doctype}: {str(e)}"
				)
	except Exception as e:
		frappe.log_error("Demo Deletion Error", f"Failed to delete masters: {str(e)}")


def delete_demo_record(item: dict[str, Any]) -> None:
	"""Delete a single demo record, bypassing permissions and link checks.

	Args:
	    item: Dictionary containing the record data to identify what to delete
	"""
	try:
		doctype = item.get("doctype")
		if not doctype:
			frappe.log_error("Demo Deletion Error", f"Missing doctype in item: {item}")
			return

		companies = demo_company_names()
		filters: dict[str, str | int | float | bool | tuple] = {
			field: (("in", companies) if field == "company" and companies else value)
			for field, value in item.items()
			if field != "doctype" and isinstance(value, (str, int, float, bool))
		}

		if not filters or not frappe.db.exists(doctype, filters):
			return

		name = frappe.db.get_value(doctype, filters, "name")
		save_point = _savepoint_name(f"delete_{doctype}")
		frappe.db.savepoint(save_point)
		try:
			frappe.delete_doc(doctype, name, force=True, ignore_permissions=True)
		except Exception:
			# Remaining links mean a demo record still points at this master;
			# the demo company is going away, so force the deletion anyway.
			frappe.db.rollback(save_point=save_point)
			frappe.delete_doc(doctype, name, force=True, ignore_permissions=True, ignore_links=True)
			frappe.logger().warning(f"Deleted {doctype} {name} while ignoring links")

		frappe.logger().debug(f"Deleted record for {doctype} with filters {filters}")
	except Exception as e:
		frappe.log_error(
			"Demo Deletion Error",
			f"Failed to delete demo record for {item.get('doctype', 'Unknown')}: {str(e)}",
		)
