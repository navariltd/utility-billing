import frappe
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
        data: Optional[Dict[str, Any]] = safe_load_json("property.json")
        if not data:
            logger.warning("property.json file missing or invalid")
            return

        logger.info("Starting demo setup...")

        create_sample_company()

        insert_from_json("customer_group.json", "Customer Group", "customer_group_name")
        insert_from_json("customers.json", "Customer", "customer_name")

        insert_feature_types(data.get("utility_property_feature_types", []))
        insert_property_features(data.get("utility_property_features", []))
        insert_unit_types(data.get("utility_property_unit_types", []))
        insert_property_categories(data.get("utility_categories", {}))
        create_asset_categories(data.get("asset_categories", []))
        create_locations(data.get("locations", []))
        
        insert_properties(data)
        
        billing_setup()
        
        insert_from_json("insurance_types.json", "Insurance Type", "name")
        insert_from_json("utility_request_types.json", "Issue Type", "name")
        insert_from_json("suppliers.json", "Supplier", "supplier_name")
        
        structures_setup()
        
        service_request_setup()

        logger.info("Demo setup completed successfully.")
        
    except Exception:
        logger.exception("Demo setup failed")
