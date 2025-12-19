import frappe


def execute():
	try:
		default_company = frappe.defaults.get_global_default("company")
		if not default_company:
			frappe.log_error("Default company not set in Global Defaults.", "Enable Frappe CRM")
			return

		doc = frappe.get_doc("ERPNext CRM Settings", "ERPNext CRM Settings")
		if doc.enabled:
			frappe.log_error("Frappe CRM is already enabled.", "Enable Frappe CRM")
			return

		doc.enabled = 1
		doc.erpnext_company = default_company
		doc.create_customer_on_status_change = 1
		doc.deal_status = "Won"

		doc.save()
		frappe.db.commit()
		return

	except Exception as e:
		frappe.log_error(str(e), "Enable Frappe CRM Error")
		return
