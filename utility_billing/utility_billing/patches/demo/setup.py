import frappe
import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from .company import create_sample_company
from .utils import logger, safe_load_json, insert_from_json
from .billing import billing_setup
from .service_request import structures_setup, service_request_setup
from .property_setup import (
    insert_feature_types,
    insert_property_features,
    insert_unit_types,
    insert_property_categories,
    create_asset_categories,
    create_locations,
    insert_properties,
)


def run_demo_setup() -> None:
    """
    Run the complete demo setup process.
    """
    try:
            
        logger.info("Starting demo setup...")

        # create_sample_company()
        
        process_masters()

        # data: Optional[Dict[str, Any]] = safe_load_json("property.json")
       
        
        # insert_properties(data)
        
        # billing_setup()
        
        
        # structures_setup()
        
        # service_request_setup()

        logger.info("Demo setup completed successfully.")
        
    except Exception:
        logger.exception("Demo setup failed")
        

def process_masters():
    try:
        for doctype in frappe.get_hooks("utility_demo_master_doctypes"):
            try:
                data = read_data_file_using_hooks(doctype)
                if data:
                    for item in json.loads(data):
                        create_demo_record(item)
            except Exception as e:
                frappe.log_error("Demo Setup Error", f"Failed to process master doctype {doctype}: {str(e)}")
    except Exception as e:
        frappe.log_error("Demo Setup Error", f"Failed to process masters: {str(e)}")
        
        
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
    except frappe.db.IntegrityError:
        frappe.logger().debug(f"IntegrityError for {item.get('doctype', 'Unknown')}, skipping")
    except Exception as e:
        frappe.log_error("Demo Setup Error", f"Failed to create demo record for {item.get('doctype', 'Unknown')}: {str(e)}")
 
 
def read_data_file_using_hooks(doctype):
	path = os.path.join(os.path.dirname(__file__), "data")
	with open(os.path.join(path, doctype + ".json")) as f:
		data = f.read()

	return data