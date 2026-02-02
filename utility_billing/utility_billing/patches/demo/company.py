import frappe
from pathlib import Path
from typing import Dict, Any, Optional
from .utils import logger, safe_load_json


COMPANY_NAME: Optional[str] = None
COMPANY_ABBR: Optional[str] = None


def get_unique_abbr(base_abbr: str) -> str:
    """Generate a unique company abbreviation."""
    if not frappe.db.exists("Company", {"abbr": base_abbr}):
        return base_abbr

    i = 1
    while True:
        new_abbr = f"{base_abbr}-{i}"
        if not frappe.db.exists("Company", {"abbr": new_abbr}):
            return new_abbr
        i += 1


def create_sample_company() -> None:
    """
    Create a sample company from JSON configuration.
    Handles case where company.json contains a list and picks the first entry.
    Automatically generates a new abbr if a conflict exists.
    """
    global COMPANY_NAME, COMPANY_ABBR

    data = safe_load_json("data/company.json")

    if isinstance(data, list) and data:
        company_data = data[0]
    else:
        company_data = data

    COMPANY_NAME = company_data.get("company_name")
    base_abbr = company_data.get("abbr")

    if not COMPANY_NAME or not base_abbr:
        logger.error("Company name or abbr missing in company.json")
        return

    if frappe.db.exists("Company", {"company_name": COMPANY_NAME}):
        logger.info(f"Company {COMPANY_NAME} already exists, skipping.")
        return

    COMPANY_ABBR = get_unique_abbr(base_abbr)
    company_data["abbr"] = COMPANY_ABBR

    try:
        company = frappe.get_doc({"doctype": "Company", **company_data})
        company.insert(ignore_permissions=True)
        logger.info(f"Company {COMPANY_NAME} created with abbr {COMPANY_ABBR}.")
    except Exception:
        logger.exception("Error creating company")
