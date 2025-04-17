import frappe
from ...setup.install import create_utility_property_dimension

def execute() -> None:
    try:
        create_utility_property_dimension()
    except:
        frappe.log_error(frappe.get_traceback(), "Error in create_utility_property_dimension")
