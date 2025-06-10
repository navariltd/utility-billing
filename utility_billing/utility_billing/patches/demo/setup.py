import frappe
import json
import os
from .company import create_sample_company
from .utils import logger
from .billing import insert_meter_readings, clear_meter_readings, delete_sales_orders
from .service_request import insert_bill_structures, clear_bill_structures, insert_service_requests

from erpnext.setup.demo import (
    create_transaction_deletion_record,
    delete_company,
)


def run_demo_setup() -> None:
    """
    Run the complete demo setup process.
    """
    logger.info("Starting demo setup...")
    
    try:
        frappe.db.begin()
        
        create_sample_company()
        process_masters()
        insert_meter_readings()
        insert_bill_structures()
        insert_service_requests()
        
        frappe.db.commit()
        frappe.msgprint("Demo setup completed successfully.")
        logger.info("Demo setup completed successfully.")
        
    except Exception as e:
        frappe.db.rollback()
        error_msg = f"Demo setup failed: {str(e)}"
        frappe.msgprint(error_msg, indicator='red')
        logger.exception(error_msg)
        raise


def delete_demo_data() -> None:
    """
    Delete all demo data created by the setup process.
    """
    logger.info("Starting demo data deletion...")
    
    try:
        frappe.db.begin()
        company = "Utility and Rental (Demo)"
        
        create_transaction_deletion_record(company)
        process_masters_deletion()
        delete_sales_orders()
        clear_meter_readings()
        clear_bill_structures()
        delete_company(company)
        
        frappe.db.commit()
        frappe.msgprint("Demo data deletion completed successfully.")
        logger.info("Demo data deletion completed successfully.")
        
    except Exception as e:
        frappe.db.rollback()
        error_msg = f"Demo data deletion failed: {str(e)}"
        frappe.msgprint(error_msg, indicator='red')
        logger.exception(error_msg)
        raise


def process_masters():
    try:
        for doctype in frappe.get_hooks("utility_demo_master_doctypes"):
            try:
                data = read_data_file_using_hooks(doctype)
                if data:
                    for item in json.loads(data):
                        create_demo_record(item)
            except Exception as e:
                error_msg = f"Failed to process master doctype {doctype}: {str(e)}"
                frappe.msgprint(error_msg, indicator='orange')
                logger.error(error_msg)
    except Exception as e:
        error_msg = f"Failed to process masters: {str(e)}"
        frappe.msgprint(error_msg, indicator='red')
        logger.error(error_msg)
        raise

        
def create_demo_record(item):
    try:
        # Extract doctype from the item
        doctype = item.get("doctype")
        if not doctype:
            frappe.log_error("Demo Setup Error", f"Missing doctype in item: {item}")
            return
            
        filters = {}
        for field, value in item.items():
            if field != "doctype" and isinstance(value, (str, int, float, bool)) and not isinstance(value, list) and not isinstance(value, dict):
                filters[field] = value

                
        if filters and frappe.db.exists(doctype, filters):
            frappe.logger().debug(f"Record already exists for {doctype} with filters {filters}")
            return
            
        doc = frappe.get_doc(item)
        doc.insert(ignore_permissions=True)
    except frappe.exceptions.DuplicateEntryError:
        frappe.logger().debug(f"Duplicate record for {item.get('doctype', 'Unknown')}, skipping")
    except Exception as e:
        frappe.log_error("Demo Setup Error", f"Failed to create demo record for {item.get('doctype', 'Unknown')}: {str(e)}")
 
 
def read_data_file_using_hooks(doctype):
	path = os.path.join(os.path.dirname(__file__), "data")
	with open(os.path.join(path, doctype + ".json")) as f:
		data = f.read()

	return data


def process_masters_deletion():
    try:
        # Process doctypes in reverse order to handle dependencies
        for doctype in reversed(frappe.get_hooks("utility_demo_master_doctypes")):
            try:
                data = read_data_file_using_hooks(doctype)
                if data:
                    for item in reversed(json.loads(data)):
                        delete_demo_record(item)
            except Exception as e:
                frappe.log_error("Demo Deletion Error", f"Failed to process deletion for doctype {doctype}: {str(e)}")
    except Exception as e:
        frappe.log_error("Demo Deletion Error", f"Failed to delete masters: {str(e)}")


def delete_demo_record(item):
    try:
        # Extract doctype from the item
        doctype = item.get("doctype")
        if not doctype:
            frappe.log_error("Demo Deletion Error", f"Missing doctype in item: {item}")
            return
            
        filters = {}
        for field, value in item.items():
            if field != "doctype" and isinstance(value, (str, int, float, bool)) and not isinstance(value, list) and not isinstance(value, dict):
                filters[field] = value
                
        if filters and frappe.db.exists(doctype, filters):
            frappe.delete_doc(doctype, frappe.db.get_value(doctype, filters, 'name'), force=True)
            frappe.logger().debug(f"Deleted record for {doctype} with filters {filters}")
    except Exception as e:
        frappe.log_error("Demo Deletion Error", f"Failed to delete demo record for {item.get('doctype', 'Unknown')}: {str(e)}")
