import frappe
from frappe import _
from ..utility_billing.patches.demo.setup import run_demo_setup


@frappe.whitelist()
def setup_demo_data():
	from frappe.utils.telemetry import capture

	try:
		run_demo_setup()
		frappe.publish_realtime("demo_data_complete")
	except Exception:
		frappe.log_error("Failed to create demo data")
		capture("demo_data_creation_failed", "utility_billing", properties={"exception": frappe.get_traceback()})
		raise
	capture("demo_data_creation_completed", "utility_billing")

 
@frappe.whitelist()
def clear_demo_data():

	frappe.only_for("System Manager")

	try:
		company = frappe.db.get_single_value("Global Defaults", "demo_company")
		create_transaction_deletion_record(company)
		clear_masters()
		delete_company(company)
		default_company = frappe.db.get_single_value("Global Defaults", "default_company")
		frappe.db.set_default("company", default_company)
	except Exception:
		frappe.db.rollback()
		frappe.log_error("Failed to erase demo data")
		frappe.throw(
			_("Failed to erase demo data, please delete the demo company manually."),
			title=_("Could Not Delete Demo Data"),
		)