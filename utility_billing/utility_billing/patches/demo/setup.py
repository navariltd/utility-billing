import json
import os
from typing import Any

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
from .utils import logger


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


def run_demo_setup() -> None:
	"""Run the complete demo setup process."""
	logger.info("Starting demo setup...")

	try:
		frappe.db.begin()

		create_sample_company()
		reset_fiscal_year_cache()
		ensure_current_fiscal_year()
		ensure_demo_price_lists()
		process_masters()
		configure_demo_settings()
		create_portal_users()
		insert_bill_structures()
		service_requests = insert_service_requests()
		create_demo_rent_item_prices(service_requests)
		insert_meter_readings()
		create_demo_transactions(service_requests)
		create_demo_support_issues()

		frappe.db.commit()
		frappe.msgprint("Demo setup completed successfully.")
		logger.info("Demo setup completed successfully.")
	except Exception as e:
		frappe.db.rollback()
		error_msg = f"Demo setup failed: {str(e)}"
		frappe.msgprint(error_msg, indicator="red")
		logger.exception(error_msg)
		raise


def delete_demo_data() -> None:
	"""Delete all demo data created by the setup process."""
	logger.info("Starting demo data deletion...")

	try:
		frappe.db.begin()
		companies = demo_company_names()

		delete_demo_auto_repeats()
		for company in companies:
			if _company_has_transactions(company):
				create_transaction_deletion_record(company)
				break
		delete_sales_orders()
		clear_meter_readings()
		clear_existing_contracts()
		clear_service_requests()
		clear_bill_structures()
		clear_demo_support_issues()
		delete_demo_property_item_prices()
		delete_demo_portal_users()
		delete_assets(companies)
		process_masters_deletion()
		delete_demo_property_service_items()
		_delete_company_child_rows(companies)
		for company in companies:
			delete_company(company)

		frappe.db.commit()
		frappe.msgprint("Demo data deletion completed successfully.")
		logger.info("Demo data deletion completed successfully.")
	except Exception as e:
		frappe.db.rollback()
		error_msg = f"Demo data deletion failed: {str(e)}"
		frappe.msgprint(error_msg, indicator="red")
		logger.exception(error_msg)
		raise


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
	"""Create a single demo record in the database.

	Args:
	    item: Dictionary containing the record data to be inserted
	"""
	try:
		# Extract doctype from the item
		doctype = item.get("doctype")
		if not doctype:
			frappe.log_error("Demo Setup Error", f"Missing doctype in item: {item}")
			return

		if doctype == "Item Price" and item.get("item_code"):
			stock_uom = frappe.db.get_value("Item", item["item_code"], "stock_uom")
			if stock_uom:
				item["uom"] = stock_uom

		filters: dict[str, str | int | float | bool] = {}
		for field, value in item.items():
			# Only add primitive types to filters, excluding lists and dictionaries
			if (
				field != "doctype"
				and isinstance(value, (str, int, float, bool))
				and not isinstance(value, list)
				and not isinstance(value, dict)
			):
				filters[field] = value

		if filters and frappe.db.exists(doctype, filters):
			frappe.logger().debug(f"Record already exists for {doctype} with filters {filters}")
			return

		doc = frappe.get_doc(item)
		doc.insert(ignore_permissions=True, ignore_mandatory=True, ignore_links=True)
	except frappe.exceptions.DuplicateEntryError:
		frappe.logger().debug(f"Duplicate record for {item.get('doctype', 'Unknown')}, skipping")
	except Exception as e:
		frappe.log_error(
			"Demo Setup Error", f"Failed to create demo record for {item.get('doctype', 'Unknown')}: {str(e)}"
		)


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
			try:
				data = read_data_file_using_hooks(doctype)
				if data:
					for item in reversed(json.loads(data)):
						delete_demo_record(item)
			except Exception as e:
				frappe.log_error(
					"Demo Deletion Error", f"Failed to process deletion for doctype {doctype}: {str(e)}"
				)
	except Exception as e:
		frappe.log_error("Demo Deletion Error", f"Failed to delete masters: {str(e)}")


def delete_demo_record(item: dict[str, Any]) -> None:
	"""Delete a single demo record from the database.

	Args:
	    item: Dictionary containing the record data to identify what to delete
	"""
	try:
		# Extract doctype from the item
		doctype = item.get("doctype")
		if not doctype:
			frappe.log_error("Demo Deletion Error", f"Missing doctype in item: {item}")
			return

		companies = demo_company_names()
		filters: dict[str, str | int | float | bool | tuple] = {}
		for field, value in item.items():
			if (
				field != "doctype"
				and isinstance(value, (str, int, float, bool))
				and not isinstance(value, list)
				and not isinstance(value, dict)
			):
				if field == "company" and companies:
					filters[field] = ("in", companies)
				else:
					filters[field] = value

		if filters and frappe.db.exists(doctype, filters):
			frappe.delete_doc(doctype, frappe.db.get_value(doctype, filters, "name"), force=True)
			frappe.logger().debug(f"Deleted record for {doctype} with filters {filters}")
	except Exception as e:
		frappe.log_error(
			"Demo Deletion Error",
			f"Failed to delete demo record for {item.get('doctype', 'Unknown')}: {str(e)}",
		)
