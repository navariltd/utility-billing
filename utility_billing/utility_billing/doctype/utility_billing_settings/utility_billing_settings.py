# Copyright (c) 2024, Navari and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

class UtilityBillingSettings(Document):
	def validate(self):
		self.validate_deferred_accounts()
		self.validate_default_parent_cost_centers()

	def validate_deferred_accounts(self):
		"""Ensure each company is mapped to a single deferred account."""
		companies = [
			row.company for row in self.get("deferred_accounts") or [] if row.company
		]

		if len(companies) != len(set(companies)):
			frappe.throw(_("Each company can only be mapped to one deferred account."))

	def validate_default_parent_cost_centers(self):
		"""Ensure each company is mapped to a single, valid parent Cost Center.

		The client filters this field to groups of the row's own company, but
		that is UX only - this is the actual guarantee.
		"""
		rows = [row for row in self.get("default_parent_cost_centers") or [] if row.company]
		companies = [row.company for row in rows]

		if len(companies) != len(set(companies)):
			frappe.throw(_("Each company can only be mapped to one default Parent Cost Center."))

		for row in rows:
			if not row.parent_cost_center:
				continue

			is_group, cost_center_company = frappe.db.get_value(
				"Cost Center", row.parent_cost_center, ["is_group", "company"]
			)

			if not is_group:
				frappe.throw(
					_("Row #{0}: {1} is not a Group Cost Center and cannot be a Parent Cost Center.").format(
						row.idx, frappe.bold(row.parent_cost_center)
					)
				)

			if cost_center_company != row.company:
				frappe.throw(
					_("Row #{0}: Parent Cost Center {1} belongs to {2}, not {3}.").format(
						row.idx, frappe.bold(row.parent_cost_center), cost_center_company, row.company
					)
				)

	def on_change(self):
		self.update_tenancy_end_notification()

	def update_tenancy_end_notification(self):
		"""Update or create the tenancy end notification based on months in advance."""
		months = self.months_in_advance_to_notify_of_tenancy_ending or 6
		days_in_advance = months * 30  

		notification_name = "Tenancy End Notification"

		if not frappe.db.exists("Notification", notification_name):
			frappe.get_doc({
				"doctype": "Notification",
				"name": notification_name,
				"subject": "Tenancy Ending: {{ doc.utility_property }}",
				"document_type": "Contract Utility Property Item",
				"module": "Utility Billing",
				"event": "Days After",
				"days_in_advance": days_in_advance,
				"date_changed": "end_date",
				"send_system_notification": 1,
				"enabled": 1,
				"message": """
<h3>Tenancy Contract Expiry</h3>

<p>The tenancy for <strong>{{ doc.utility_property }}</strong> is ending soon.</p>

<h4>Contract Period</h4>
<ul>
    <li><strong>Start Date:</strong> {{ doc.start_date or 'N/A' }}</li>
    <li><strong>End Date:</strong> {{ doc.end_date or 'N/A' }}</li>
</ul>

<p>Kindly review or renew the tenancy if necessary.</p>
""",
				"recipients": [
					{"receiver_by_role": "Property Manager"},
					{"receiver_by_role": "Property User"},
				]
			}).insert(ignore_permissions=True)
		else:
			frappe.db.set_value("Notification", notification_name, "days_in_advance", days_in_advance)
			frappe.db.commit()