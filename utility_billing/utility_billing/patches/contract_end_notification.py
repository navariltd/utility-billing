import frappe


def execute():
	if not frappe.db.exists("Notification", "Property Contract End Notification"):
		frappe.get_doc(
			{
				"doctype": "Notification",
				"name": "Property Contract End Notification",
				"subject": "Contract Ending: {{ doc.utility_property }}",
				"document_type": "Contract Utility Property Item",
				"module": "Utility Billing",
				"event": "Days After",
				"days_in_advance": 1,
				"date_changed": "end_date",
				"send_system_notification": 1,
				"set_property_after_alert": "is_active",
				"property_value": "0",
				"enabled": 1,
				"message": """
<h3>Utility Property Contract Expiry</h3>

<p>The contract for <strong>{{ doc.utility_property }}</strong> is ending soon.</p>

{% if comments %}
<p><strong>Last Comment:</strong> {{ comments[-1].comment }} by {{ comments[-1].by }}</p>
{% endif %}

<h4>Contract Period</h4>
<ul>
    <li><strong>Start Date:</strong> {{ doc.start_date or 'N/A' }}</li>
    <li><strong>End Date:</strong> {{ doc.end_date or 'N/A' }}</li>
</ul>

<p>Kindly review or renew the contract if necessary.</p>
""",
				"recipients": [
					{"receiver_by_role": "Property Manager"},
					{"receiver_by_role": "Property User"},
				],
			}
		).insert(ignore_permissions=True)
