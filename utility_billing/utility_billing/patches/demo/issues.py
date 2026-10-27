"""Portal support tickets for the demo tenants.

The tickets are standard ``Issue`` documents linked to the tenant's Customer,
property and originating Utility Service Request. A few of them include a
support reply so the portal timeline and status counts have data to show.
"""

import frappe
from frappe.utils import add_days, today

from .constants import DEMO_COMPANY, demo_company_names
from .customers import resolve_customer
from .portal_users import get_demo_user_email
from .utils import logger, safe_load_json

ISSUE_FILE = "data/support_issue.json"
ISSUE_TYPE_DOCTYPE = "Issue Type"
ISSUE_SAVEPOINT = "demo_support_issue"


def create_demo_support_issues() -> None:
	"""Create the demo support tickets and their first replies."""
	issues = safe_load_json(ISSUE_FILE) or []
	requests_by_property = _requests_by_property()

	for record in issues:
		frappe.db.savepoint(ISSUE_SAVEPOINT)
		try:
			_create_issue(record, requests_by_property)
		except Exception:
			frappe.db.rollback(save_point=ISSUE_SAVEPOINT)
			logger.exception(f"Could not create demo support issue {record.get('subject')}")


def clear_demo_support_issues() -> None:
	"""Delete the support tickets created for the demo companies."""
	companies = demo_company_names()
	if not companies:
		return

	names = frappe.get_all("Issue", filters={"company": ("in", companies)}, pluck="name")
	if names:
		frappe.db.delete(
			"Comment",
			{"reference_doctype": "Issue", "reference_name": ("in", names)},
		)

	for name in names:
		frappe.delete_doc("Issue", name, force=True, ignore_permissions=True)


def _requests_by_property() -> dict[str, str]:
	"""Map each demo property to the submitted request that leased it."""
	requests = {
		row.name: row
		for row in frappe.get_all(
			"Utility Service Request",
			filters={"company": DEMO_COMPANY, "docstatus": 1},
			fields=["name", "customer"],
			order_by="creation desc",
		)
	}

	rows = frappe.get_all(
		"Contract Utility Property Item",
		filters={"parenttype": "Utility Service Request"},
		fields=["parent", "utility_property"],
		order_by="creation desc",
	)

	result = {}
	for row in rows:
		if row.parent in requests and row.utility_property not in result:
			result[row.utility_property] = row.parent

	return result


def _create_issue(record: dict, requests_by_property: dict[str, str]) -> str | None:
	"""Create one demo Issue and its optional support reply."""
	subject = record.get("subject")
	customer_reference = record.get("customer")
	property_name = record.get("property")
	customer = resolve_customer(customer_reference)
	if not (subject and customer and property_name):
		return None

	if frappe.db.exists(
		"Issue",
		{
			"customer": customer.name,
			"subject": subject,
			"utility_property": property_name,
		},
	):
		return None

	issue_type = record.get("issue_type")
	if issue_type and not frappe.db.exists(ISSUE_TYPE_DOCTYPE, issue_type):
		issue_type = None

	opening_date = add_days(today(), -(record.get("days_ago") or 0))
	issue = frappe.get_doc(
		{
			"doctype": "Issue",
			"naming_series": "ISS-.YYYY.-",
			"subject": subject,
			"description": f"<p>{record.get('description') or ''}</p>",
			"customer": customer.name,
			"customer_name": customer.customer_name,
			"raised_by": get_demo_user_email(customer_reference),
			"company": DEMO_COMPANY,
			"status": record.get("status") or "Open",
			"priority": record.get("priority") or "Medium",
			"issue_type": issue_type,
			"opening_date": opening_date,
			"via_customer_portal": 1,
			"utility_property": property_name,
			"utility_service_request": requests_by_property.get(property_name),
		}
	)
	issue.flags.ignore_permissions = True
	issue.insert()

	reply = (record.get("reply") or "").strip()
	if reply:
		frappe.get_doc(
			{
				"doctype": "Comment",
				"comment_type": "Comment",
				"reference_doctype": "Issue",
				"reference_name": issue.name,
				"comment_email": "Administrator",
				"comment_by": "Demo Support",
				"content": f"<p>{reply}</p>",
			}
		).insert(ignore_permissions=True)

	return issue.name
