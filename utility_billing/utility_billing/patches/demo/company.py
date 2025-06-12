import frappe
from pathlib import Path
from typing import Dict, Any, Optional
from .utils import logger, safe_load_json


COMPANY_NAME: Optional[str] = None
COMPANY_ABBR: Optional[str] = None


def create_sample_company() -> None:
    """
    Create a sample company from JSON configuration.
    Handles case where company.json contains a list and picks the first entry.
    
    Returns:
        None
    """
    global COMPANY_NAME, COMPANY_ABBR

    data = safe_load_json("data/company.json")
    
    # Handle case where data is a list
    if isinstance(data, list) and data:
        company_data = data[0]
    else:
        company_data = data

    COMPANY_NAME = company_data.get("company_name")
    COMPANY_ABBR = company_data.get("abbr")

    if not COMPANY_NAME or frappe.db.exists("Company", COMPANY_NAME):
        return

    try:
        company = frappe.get_doc({"doctype": "Company", **company_data})
        company.insert()
        logger.info(f"Company {COMPANY_NAME} created successfully.")
    except Exception:
        logger.exception("Error creating company")
