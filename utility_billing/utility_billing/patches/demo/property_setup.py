import frappe
import random
from typing import Dict, List, Optional, Any, Union
from .utils import safe_insert_doc, get_doc_or_create
from .company import COMPANY_NAME, COMPANY_ABBR


def insert_feature_types(feature_types: List[str]) -> None:
    """Insert feature types into the system.
    
    Args:
        feature_types: List of feature type names to insert
    """
    for ftype in feature_types:
        safe_insert_doc(
            "Utility Property Feature Type",
            {"doctype": "Utility Property Feature Type", "feature_type": ftype},
            unique_key="feature_type"
        )


def insert_property_features(features: List[str]) -> None:
    """Insert property features into the system.
    
    Args:
        features: List of feature names to insert
    """
    for feature in features:
        safe_insert_doc(
            "Utility Property Feature",
            {"doctype": "Utility Property Feature", "feature": feature},
            unique_key="feature"
        )


def insert_unit_types(unit_types: List[str]) -> None:
    """Insert unit types into the system.
    
    Args:
        unit_types: List of unit type names to insert
    """
    for unit in unit_types:
        safe_insert_doc(
            "Utility Property Unit Type",
            {"doctype": "Utility Property Unit Type", "unit_type": unit},
            unique_key="unit_type"
        )


def insert_property_categories(categories_dict: Dict[str, List[str]]) -> None:
    """Insert property categories into the system.
    
    Args:
        categories_dict: Dictionary mapping parent categories to lists of child categories
    """
    for parent, children in categories_dict.items():
        if frappe.db.exists("Utility Category", parent):
            parent_doc = frappe.get_doc("Utility Category", parent)
        else:
            parent_doc = frappe.get_doc({
                "doctype": "Utility Category",
                "title": parent,
                "is_group": 1
            }).insert()

        for child in children:
            if frappe.db.exists("Utility Category", child):
                continue
            frappe.get_doc({
                "doctype": "Utility Category",
                "title": child,
                "is_group": 0,
                "parent_utility_category": parent_doc.name
            }).insert()


def create_asset_categories(categories: List[str]) -> None:
    """Create asset categories in the system.
    
    Args:
        categories: List of asset category names to create
    """
    for category in categories:
        safe_insert_doc(
            "Asset Category",
            {
                "doctype": "Asset Category",
                "asset_category_name": category,
                "enable_cwip_accounting": 0,
                "accounts": [
                    {
                        "company_name": COMPANY_NAME,
                        "fixed_asset_account": f"Buildings - {COMPANY_ABBR}",
                        "accumulated_depreciation_account": f"Accumulated Depreciation - {COMPANY_ABBR}",
                        "depreciation_expense_account": f"Depreciation - {COMPANY_ABBR}",
                        "capital_work_in_progress_account": f"CWIP Account - {COMPANY_ABBR}",
                    }
                ],
            },
            unique_key="asset_category_name"
        )


def create_locations(locations: List[str]) -> None:
    """Create locations in the system.
    
    Args:
        locations: List of location names to create
    """
    safe_insert_doc(
        "Location",
        {"doctype": "Location", "location_name": "All Locations", "is_group": 1},
        unique_key="location_name"
    )

    for location in locations:
        safe_insert_doc(
            "Location",
            {
                "doctype": "Location",
                "location_name": location,
                "is_group": 0,
                "parent_location": "All Locations",
            },
            unique_key="location_name"
        )


def insert_properties(data: Dict[str, Any]) -> None:
    """Insert properties into the system.
    
    Args:
        data: Dictionary containing property data and related information
    """
    try:
        categories = frappe.get_all("Utility Category", fields=["name", "title"])
        category_map = {c["title"]: c["name"] for c in categories}
    except Exception:
        import logging
        logging.exception("Error fetching Utility Categories")
        return

    for prop in data.get("utility_properties", []):
        try:
            if frappe.db.exists("Utility Property", {"property_name": prop["name"]}):
                parent_doc = frappe.get_doc("Utility Property", {"property_name": prop["name"]})
            else:
                parent_doc = frappe.get_doc({
                    "doctype": "Utility Property",
                    "property_name": prop["name"],
                    "utility_category": category_map.get(prop["category"]),
                    "company": COMPANY_NAME,
                    "status": prop.get("status", "Available"),
                    "is_fixed_asset": prop.get("is_fixed_asset", 0),
                    "is_group": 1,
                    "unit_type": prop.get("unit_type"),
                    "asset_category": prop.get("asset_category"),
                    "gross_purchase_amount": prop.get("gross_purchase_amount", 0),
                    "location": prop.get("location"),
                    "bedrooms": prop.get("bedrooms", 0),
                    "bathrooms": prop.get("bathrooms", 0)
                })

                for feature in prop.get("features", []):
                    parent_doc.append("features", {
                        "feature": feature,
                        "feature_type": random.choice(data.get("utility_property_feature_types", [])) if data.get("utility_property_feature_types") else None,
                        "notes": f"{feature} included"
                    })

                parent_doc.insert()

            for unit in prop.get("units", []):
                unit_name = unit["name"]
                if frappe.db.exists("Utility Property", {"property_name": unit_name}):
                    continue

                unit_doc = frappe.get_doc({
                    "doctype": "Utility Property",
                    "property_name": unit_name,
                    "utility_category": category_map.get(prop["category"]),
                    "parent_utility_property": parent_doc.name,
                    "company": COMPANY_NAME,
                    "status": unit.get("status", "Available"),
                    "is_fixed_asset": unit.get("is_fixed_asset", 0),
                    "unit_type": unit.get("unit_type"),
                    "bedrooms": unit.get("bedrooms", 0),
                    "bathrooms": unit.get("bathrooms", 0),
                    "monthly_rent": unit.get("monthly_rent", 0),
                    "size_sqft": unit.get("size_sqft", 0),
                    "location": prop.get("location")
                })
                unit_doc.insert()

        except Exception:
            import logging
            logging.exception(f"Error inserting property {prop.get('name')}")
