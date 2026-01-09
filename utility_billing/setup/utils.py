import frappe
from erpnext.setup.utils import enable_all_roles_and_domains
from frappe.utils import now_datetime


def before_tests():
	frappe.clear_cache()
	# complete setup if missing
	from frappe.desk.page.setup_wizard.setup_wizard import setup_complete

	year = now_datetime().year
	if not frappe.get_list("Company"):
		setup_complete(
			{
				"currency": "KES",
				"full_name": "Test User",
				"company_name": "Navari Limited",
				"timezone": "Africa/Nairobi",
				"company_abbr": "NL",
				"industry": "Software",
				"country": "Kenya",
				"fy_start_date": f"{year}-01-01",
				"fy_end_date": f"{year}-12-31",
				"language": "english",
				"company_tagline": "Testing",
				"email": "test@navari.co.ke",
				"password": "test",
				"chart_of_accounts": "Standard",
			}
		)

	enable_all_roles_and_domains()
	# Manually commit to save setup progress in case of timeout
	frappe.db.commit()  # nosemgrep
