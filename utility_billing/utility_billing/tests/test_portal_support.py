"""Unit tests for portal support ticket summaries and timelines."""

import json
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase, UnitTestCase

from utility_billing.api.portal.support import (
	create_support_issue,
	get_booking_support,
	get_support_issue,
	reply_to_support_issue,
)
from utility_billing.api.portal.support_payload import (
	issue_counts,
	issue_detail,
	issue_summary,
	message_html,
)
from utility_billing.api.portal.support_timeline import version_events


class TestSupportMessages(UnitTestCase):
	"""Customer messages are rendered safely for the conversation timeline."""

	def test_plain_text_is_escaped_and_newlines_preserved(self):
		html = message_html("Rent < 5000 & deposit\nDue tomorrow")

		self.assertIn("&lt; 5000", html)
		self.assertIn("&amp; deposit", html)
		self.assertIn("<br>", html)
		self.assertNotIn("<script", html)

	def test_rich_text_is_sanitised(self):
		html = message_html("<p>Hello</p><script>alert('x')</script>")

		self.assertIn("<p>Hello</p>", html)
		self.assertNotIn("<script", html)

	def test_blank_message_returns_empty_html(self):
		self.assertEqual(message_html("   "), "")


class TestSupportIssues(UnitTestCase):
	"""Issue rows are summarised for the booking support list."""

	def test_summary_uses_plain_text_snippet_and_open_state(self):
		issue = frappe._dict(
			name="ISS-0001",
			subject="Leaking tap",
			status="Open",
			priority="High",
			issue_type="Property Lease",
			opening_date="2026-10-26",
			creation="2026-10-26 10:00:00",
			modified="2026-10-26 10:00:00",
			resolution_time=None,
			first_responded_on=None,
			agreement_status="First Response Due",
			via_customer_portal=1,
			customer="C0001",
			customer_name="Jane Doe",
			raised_by="jane@example.com",
			utility_property="PROP-1",
			utility_service_request="USR-1",
			description="<p>Water is dripping onto the floor.</p>",
		)

		summary = issue_summary(issue)

		self.assertTrue(summary["is_open"])
		self.assertEqual(summary["snippet"], "Water is dripping onto the floor.")
		self.assertEqual(summary["property"], "PROP-1")
		self.assertEqual(summary["service_request"], "USR-1")
		self.assertNotIn("description", summary)

	def test_detail_includes_sanitised_description_and_resolution(self):
		issue = frappe._dict(
			name="ISS-0002",
			subject="No water",
			status="Resolved",
			priority=None,
			issue_type=None,
			opening_date="2026-10-26",
			creation="2026-10-26 10:00:00",
			modified="2026-10-26 12:00:00",
			resolution_time=7200,
			first_responded_on="2026-10-26 10:30:00",
			agreement_status="Fulfilled",
			via_customer_portal=1,
			customer="C0001",
			customer_name=None,
			raised_by="jane@example.com",
			utility_property=None,
			utility_service_request=None,
			description="<p>No water since morning.</p>",
			resolution_details="<p>Meter valve replaced.</p>",
		)

		detail = issue_detail(issue)

		self.assertFalse(detail["is_open"])
		self.assertEqual(detail["description"], "<p>No water since morning.</p>")
		self.assertEqual(detail["resolution_details"], "<p>Meter valve replaced.</p>")

	def test_counts_split_open_replied_and_resolved(self):
		counts = issue_counts(
			[
				{"status": "Open"},
				{"status": "On Hold"},
				{"status": "Replied"},
				{"status": "Resolved"},
				{"status": "Closed"},
			]
		)

		self.assertEqual(counts["open"], 2)
		self.assertEqual(counts["replied"], 1)
		self.assertEqual(counts["resolved"], 2)
		self.assertEqual(counts["total"], 5)


class TestSupportVersionEvents(UnitTestCase):
	"""Status updates from Issue Version records become timeline events."""

	def test_tracked_changes_become_events(self):
		version = frappe._dict(
			name="ver-1",
			owner="agent@example.com",
			creation="2026-10-26 11:00:00",
			data=json.dumps(
				{
					"changed": [
						["Issue", "ISS-0001", "status", "Open", "Replied"],
						["Issue", "ISS-0001", "description", "old", "new"],
						["Issue", "ISS-0001", "status", "Open", "Open"],
					]
				}
			),
		)

		events = version_events(version)

		self.assertEqual(len(events), 1)
		self.assertEqual(events[0]["type"], "status")
		self.assertEqual(events[0]["field"], "status")
		self.assertEqual(events[0]["old_value"], "Open")
		self.assertEqual(events[0]["new_value"], "Replied")

	def test_malformed_version_data_is_ignored(self):
		version = frappe._dict(
			name="ver-2",
			owner="agent@example.com",
			creation="2026-10-26 11:00:00",
			data="{not json",
		)

		self.assertEqual(version_events(version), [])


class TestSupportEndpoints(IntegrationTestCase):
	"""Creating and replying links the ticket to the booking and customer."""

	def test_ticket_is_linked_to_booking_and_replies_are_recorded(self):
		customer_doc = frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": f"Support Test {frappe.generate_hash(length=6)}",
				"customer_type": "Individual",
			}
		).insert(ignore_permissions=True)
		customer = customer_doc.name
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": f"support-{frappe.generate_hash(length=8)}@example.com",
				"first_name": "Support",
				"last_name": "Tester",
				"send_welcome_email": 0,
			}
		).insert(ignore_permissions=True)
		request = frappe._dict(
			name="USR-SUPPORT-TEST",
			customer=customer,
			customer_name=customer,
			company=frappe.db.get_value("Company", {}, "name"),
			requested_properties=[],
		)

		frappe.set_user(user.name)
		try:
			with (
				patch(
					"utility_billing.api.portal.support_context.get_own_request",
					return_value=request,
				),
				patch("frappe.model.document.Document._validate_links", lambda self: None),
			):
				created = create_support_issue(
					request.name,
					"Leaking kitchen tap",
					"Water has been dripping under the sink since this morning.",
				)
				workspace = get_booking_support(request.name)
				reply = reply_to_support_issue(
					created["issue"]["name"],
					"Still leaking after tightening the valve.",
				)
				detail = get_support_issue(created["issue"]["name"])
		finally:
			frappe.set_user("Administrator")

		self.assertEqual(created["issue"]["service_request"], request.name)
		self.assertEqual(created["issue"]["customer"], customer)
		self.assertEqual(created["issue"]["status"], "Open")
		self.assertEqual(created["issue"]["raised_by"], user.name)
		self.assertTrue(created["issue"]["via_customer_portal"])
		self.assertEqual(workspace["counts"]["open"], 1)
		self.assertIn(
			created["issue"]["name"],
			[issue["name"] for issue in workspace["issues"]],
		)

		comments = [event for event in reply["timeline"] if event["type"] == "comment"]
		self.assertEqual(len(comments), 1)
		self.assertEqual(comments[0]["author_type"], "customer")
		self.assertIn("Still leaking", comments[0]["content"])
		self.assertEqual(detail["issue"]["name"], created["issue"]["name"])
