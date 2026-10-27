"""Conversation timeline for a portal support ticket.

Merges customer-visible Issue communications, comments and tracked status
changes into one chronological feed.
"""

import json
from collections.abc import Iterable

import frappe
from frappe import _

from utility_billing.api.portal.support_payload import ISSUE_DOCTYPE, message_html

TRACKED_VERSION_FIELDS = {
	"status": _("Status"),
	"priority": _("Priority"),
	"issue_type": _("Category"),
}


def get_user_labels(names: Iterable[str]) -> dict[str, str]:
	"""Return display names for the given user IDs."""
	user_names = list(dict.fromkeys(name for name in names or () if name))
	if not user_names:
		return {}

	users = frappe.db.get_all(
		"User",
		filters={"name": ("in", user_names)},
		fields=["name", "full_name"],
	)
	return {user.name: user.full_name or user.name for user in users}


def version_events(version) -> list[dict]:
	"""Return timeline events for tracked changes in a Version record."""
	try:
		data = json.loads(version.data or "{}")
	except (TypeError, ValueError):
		return []

	events = []
	for change in data.get("changed") or []:
		if not isinstance(change, (list, tuple)) or len(change) < 5:
			continue

		fieldname, old_value, new_value = change[2], change[3], change[4]
		if fieldname not in TRACKED_VERSION_FIELDS or str(old_value) == str(new_value):
			continue

		events.append(
			{
				"id": f"{version.name}-{fieldname}",
				"type": "status",
				"field": fieldname,
				"label": TRACKED_VERSION_FIELDS[fieldname],
				"old_value": old_value or _("Not set"),
				"new_value": new_value or _("Not set"),
				"date": version.creation,
				"author_id": version.owner,
				"content": "",
			}
		)

	return events


def get_issue_timeline(issue) -> list[dict]:
	"""Return the messages, comments and status changes of an Issue."""
	events = [
		{
			"id": f"{issue.name}-created",
			"type": "created",
			"date": issue.creation,
			"author_id": issue.raised_by or issue.owner,
			"content": "",
		}
	]

	events.extend(_communication_events(issue))
	events.extend(_comment_events(issue))
	events.extend(_version_events(issue))

	_apply_author_labels(events)
	return sorted(events, key=lambda event: (str(event.get("date") or ""), str(event.get("id") or "")))


def _communication_events(issue) -> list[dict]:
	fields = ["name", "subject", "content", "sender", "communication_date", "sent_or_received"]
	referenced = frappe.db.get_all(
		"Communication",
		filters={"reference_doctype": ISSUE_DOCTYPE, "reference_name": issue.name},
		fields=fields,
		order_by="communication_date asc",
	)

	link_parents = frappe.db.get_all(
		"Communication Link",
		filters={"link_doctype": ISSUE_DOCTYPE, "link_name": issue.name},
		pluck="parent",
	)
	linked = (
		frappe.db.get_all(
			"Communication",
			filters={"name": ("in", link_parents)},
			fields=fields,
			order_by="communication_date asc",
		)
		if link_parents
		else []
	)

	communications = {communication.name: communication for communication in [*referenced, *linked]}
	events = []
	for communication in communications.values():
		if not communication.content:
			continue
		events.append(
			{
				"id": communication.name,
				"type": "message",
				"date": communication.communication_date,
				"author_id": communication.sender,
				"author_type": "customer" if communication.sender == issue.raised_by else "support",
				"subject": communication.subject,
				"content": message_html(communication.content),
			}
		)

	return events


def _comment_events(issue) -> list[dict]:
	comments = frappe.db.get_all(
		"Comment",
		filters={
			"reference_doctype": ISSUE_DOCTYPE,
			"reference_name": issue.name,
			"comment_type": "Comment",
		},
		fields=["name", "content", "comment_by", "creation", "owner"],
		order_by="creation asc",
	)

	events = []
	for comment in comments:
		events.append(
			{
				"id": comment.name,
				"type": "comment",
				"date": comment.creation,
				"author_id": comment.owner,
				"author_name": comment.comment_by,
				"author_type": "customer" if comment.owner == issue.raised_by else "support",
				"content": message_html(comment.content),
			}
		)

	return events


def _version_events(issue) -> list[dict]:
	versions = frappe.db.get_all(
		"Version",
		filters={"ref_doctype": ISSUE_DOCTYPE, "docname": issue.name},
		fields=["name", "data", "creation", "owner"],
		order_by="creation asc",
	)

	events = []
	for version in versions:
		events.extend(version_events(version))

	return events


def _apply_author_labels(events: list[dict]) -> None:
	user_ids = [event.get("author_id") for event in events if event.get("author_id")]
	labels = get_user_labels(user_ids)
	for event in events:
		event["author"] = (
			event.get("author_name") or labels.get(event.get("author_id")) or event.get("author_id")
		)
		event.pop("author_name", None)
