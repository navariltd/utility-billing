import frappe
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from .company import create_sample_company
from .utils import logger, safe_load_json, insert_from_json
from .property_setup import (
    insert_feature_types,
    insert_property_features,
    insert_unit_types,
    insert_property_categories,
    create_asset_categories,
    create_locations,
    insert_properties,
)

BASE_DIR = Path(__file__).parent 

def run_demo_setup() -> None:
    """
    Run the complete demo setup process.
    """
    try:
        data: Optional[Dict[str, Any]] = safe_load_json(BASE_DIR / "property.json")
        if not data:
            logger.warning("property.json file missing or invalid")
            return

        logger.info("Starting demo setup...")

        create_sample_company()

        insert_from_json(BASE_DIR, "customers.json", "Customer", "customer_name")

        insert_feature_types(data.get("utility_property_feature_types", []))
        insert_property_features(data.get("utility_property_features", []))
        insert_unit_types(data.get("utility_property_unit_types", []))
        insert_property_categories(data.get("utility_categories", {}))
        create_asset_categories(data.get("asset_categories", []))
        create_locations(data.get("locations", []))
        
        insert_properties(data)

        logger.info("Demo setup completed successfully.")
    except Exception:
        logger.exception("Demo setup failed")
