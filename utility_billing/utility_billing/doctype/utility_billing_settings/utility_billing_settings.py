# Copyright (c) 2024, Navari and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class UtilityBillingSettings(Document):
	def on_change(self):
		self.update_tenancy_end_notification()

	def update_tenancy_end_notification(self):
		"""Update or create the tenancy end notification based on months in advance."""
		months = self.months_in_advance_to_notify_of_tenancy_ending or 6
		days_in_advance = months * 30

		notification_name = "Tenancy End Notification"

		if not frappe.db.exists("Notification", notification_name):
			frappe.get_doc(
				{
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
					],
				}
			).insert(ignore_permissions=True)
		else:
			frappe.db.set_value("Notification", notification_name, "days_in_advance", days_in_advance)
			frappe.db.commit()
