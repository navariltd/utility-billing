import frappe
from pathlib import Path
from typing import Dict, Any, Optional
from .utils import logger, safe_load_json

BASE_DIR = Path(__file__).parent 

COMPANY_NAME: Optional[str] = None
COMPANY_ABBR: Optional[str] = None


def create_sample_company() -> None:
    """
    Create a sample company from JSON configuration.
    
    Returns:
        None
    """
    global COMPANY_NAME, COMPANY_ABBR
    path = BASE_DIR / "company.json"
    if not path.exists():
        logger.warning(f"File company.json not found in {BASE_DIR}")
        return

    data: Dict[str, Any] = safe_load_json(path)

    COMPANY_NAME = data.get("company_name")
    COMPANY_ABBR = data.get("abbr")

    if not COMPANY_NAME or frappe.db.exists("Company", COMPANY_NAME):
        return

    try:
        company = frappe.get_doc({"doctype": "Company", **data})
        company.insert()
        logger.info(f"Company {COMPANY_NAME} created successfully.")
    except Exception:
        logger.exception("Error creating company")
