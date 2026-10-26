"""Read helpers and payloads for portal support tickets.

Support tickets are standard ERPNext ``Issue`` documents linked to the property
(``utility_property``), the originating booking (``utility_service_request``)
and the tenant's Customer. This module keeps issue listing and serialisation
separate from the conversation timeline and the portal endpoints.
"""

from collections.abc import Iterable
from html import escape

import frappe
from frappe.utils import strip_html
from frappe.utils.html_utils import has_html_tags

ISSUE_DOCTYPE = "Issue"

ISSUE_FIELDS = (
	"name",
	"subject",
	"status",
	"priority",
	"issue_type",
	"opening_date",
	"creation",
	"modified",
	"description",
	"resolution_details",
	"resolution_time",
	"first_responded_on",
	"agreement_status",
	"via_customer_portal",
	"customer",
	"customer_name",
	"raised_by",
	"utility_property",
	"utility_service_request",
)

RESOLVED_STATUSES = ("Resolved", "Closed")
OPEN_STATUSES = ("Open", "On Hold")


def message_html(value: str | None) -> str:
	"""Return safe HTML for a message that may be plain text or rich text.

	Plain text is escaped and newlines are preserved; rich text is sanitised
	with Frappe's HTML sanitiser before it reaches the browser.
	"""
	value = (value or "").strip()
	if not value:
		return ""

	if has_html_tags(value):
		return frappe.utils.sanitize_html(value)

	return "<p>" + escape(value).replace("\n", "<br>") + "</p>"


def message_text(value: str | None) -> str:
	"""Return the searchable text of an HTML message."""
	return " ".join(strip_html(value or "").split())


def issue_snippet(value: str | None, length: int = 180) -> str:
	"""Return a short plain-text preview of an issue description."""
	text = message_text(value)
	if len(text) <= length:
		return text

	return text[: length - 1].rstrip() + "…"


def issue_summary(issue) -> dict:
	"""Serialise an Issue row for the booking support list."""
	return {
		"name": issue.name,
		"subject": issue.subject,
		"status": issue.status,
		"priority": issue.priority,
		"issue_type": issue.issue_type,
		"opening_date": issue.opening_date,
		"creation": issue.creation,
		"modified": issue.modified,
		"resolution_time": issue.resolution_time,
		"first_responded_on": issue.first_responded_on,
		"agreement_status": issue.agreement_status,
		"via_customer_portal": issue.via_customer_portal,
		"customer": issue.customer,
		"customer_name": issue.customer_name,
		"raised_by": issue.raised_by,
		"property": issue.get("utility_property"),
		"service_request": issue.get("utility_service_request"),
		"is_open": issue.status not in RESOLVED_STATUSES,
		"snippet": issue_snippet(issue.get("description")),
	}


def issue_detail(issue) -> dict:
	"""Serialise an Issue with its full description and resolution."""
	summary = issue_summary(issue)
	summary["description"] = message_html(issue.get("description"))
	summary["resolution_details"] = message_html(issue.get("resolution_details")) or None
	return summary


def get_issue_summaries(
	property_name: str | None,
	customers: Iterable[str],
	booking: str | None = None,
) -> list[dict]:
	"""Return issues linked to a property, a booking or both.

	The Customer filter always applies; ``property_name`` and ``booking`` widen
	the match with OR semantics so a property page also sees tickets raised from
	the original booking, and vice versa.
	"""
	customer_names = list(dict.fromkeys(name for name in customers or () if name))
	if not customer_names:
		return []

	or_filters = []
	if property_name:
		or_filters.append(["utility_property", "=", property_name])
	if booking:
		or_filters.append(["utility_service_request", "=", booking])
	if not or_filters:
		return []

	issues = frappe.db.get_all(
		ISSUE_DOCTYPE,
		filters={"customer": ("in", customer_names)},
		or_filters=or_filters,
		fields=list(ISSUE_FIELDS),
		order_by="creation desc",
		limit=200,
	)

	return [issue_summary(issue) for issue in issues]


def issue_counts(issues: Iterable[dict]) -> dict:
	"""Return open, replied and resolved counts for a list of issues."""
	statuses = [issue.get("status") for issue in issues]
	open_count = sum(1 for status in statuses if status in OPEN_STATUSES)
	replied = sum(1 for status in statuses if status == "Replied")
	resolved = sum(1 for status in statuses if status in RESOLVED_STATUSES)
	return {
		"open": open_count,
		"replied": replied,
		"resolved": resolved,
		"total": len(statuses),
	}
