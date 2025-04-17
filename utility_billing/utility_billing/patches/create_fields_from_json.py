import json
import os

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def create_fields_from_json(json_file_name: str, doctype: str) -> None:
    try:
        current_dir: str = os.path.dirname(os.path.abspath(__file__))
        json_file_path: str = os.path.join(current_dir, json_file_name)

        with open(json_file_path) as f:
            custom_fields_data: list = json.load(f)

        for field in custom_fields_data:
            field["module"] = "Utility Billing"

        custom_fields: dict = {doctype: custom_fields_data}

        create_custom_fields(custom_fields, update=True)

    except Exception as e:
        frappe.log_error(
            f"Error in creating custom fields for {doctype}: {str(e)}",
            "Custom Field Creation Error",
        )
