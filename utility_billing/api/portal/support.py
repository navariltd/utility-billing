"""Portal support tickets raised from a booking or an active property.

Customers raise a standard ERPNext ``Issue``. It is linked to the property and,
when the tenancy or booking provides one, to the originating ``Utility Service
Request``, so support staff keep the full context. Responses, comments and
status changes are read back from the Issue timeline.

All endpoints enforce that the booking, property and issue belong to the
signed-in Customer before bypassing document permissions.
"""

import frappe
from frappe import _
from frappe.utils import get_fullname, nowdate

from utility_billing.api.portal.roles import require_authenticated_user
from utility_billing.api.portal.support_context import (
	get_booking_context,
	get_own_issue,
	get_property_context,
)
from utility_billing.api.portal.support_payload import (
	get_issue_summaries,
	issue_counts,
	issue_detail,
	message_html,
	message_text,
)
from utility_billing.api.portal.support_timeline import get_issue_timeline

__all__ = [
	"create_property_support_issue",
	"create_support_issue",
	"get_booking_support",
	"get_property_support",
	"get_support_issue",
	"reply_to_support_issue",
]

ISSUE_DOCTYPE = "Issue"
SUBJECT_MAX_LENGTH = 140
MESSAGE_MAX_LENGTH = 5000


@frappe.whitelist()
def get_booking_support(booking: str) -> dict:
	"""Return the support tickets linked to one of the caller's bookings.

	Args:
		booking: ``Utility Service Request`` name.

	Returns:
		Dict with the booking context, ticket summaries and status counts.

	Raises:
		frappe.PermissionError: When the booking belongs to another Customer.
	"""
	context = get_booking_context(booking)
	issues = get_issue_summaries(
		context["property"],
		[context["customer"]] if context["customer"] else [],
		booking=context["service_request"],
	)
	return _support_payload(context, issues)


@frappe.whitelist()
def get_property_support(property: str) -> dict:
	"""Return the support tickets linked to a property with an active tenancy.

	Args:
		property: ``Utility Property`` name.

	Returns:
		Dict with the tenancy context, ticket summaries and status counts.

	Raises:
		frappe.PermissionError: When the property is not actively allocated to the caller.
	"""
	context = get_property_context(property)
	issues = get_issue_summaries(
		context["property"],
		[context["customer"]] if context["customer"] else [],
		booking=context["service_request"],
	)
	return _support_payload(context, issues)


@frappe.whitelist(methods=["POST"])
def create_support_issue(booking: str, subject: str, description: str) -> dict:
	"""Raise a support ticket for a booking.

	Args:
		booking: ``Utility Service Request`` name.
		subject: Short summary shown in the support queue.
		description: What the customer needs help with.

	Returns:
		The created issue with its timeline.

	Raises:
		frappe.PermissionError: When the booking is not the caller's.
		frappe.ValidationError: When the subject or description is invalid.
	"""
	return _create_issue(get_booking_context(booking), subject, description)


@frappe.whitelist(methods=["POST"])
def create_property_support_issue(property: str, subject: str, description: str) -> dict:
	"""Raise a support ticket for a property with an active tenancy.

	Args:
		property: ``Utility Property`` name.
		subject: Short summary shown in the support queue.
		description: What the customer needs help with.

	Returns:
		The created issue with its timeline.

	Raises:
		frappe.PermissionError: When the property is not the caller's.
		frappe.ValidationError: When the subject or description is invalid.
	"""
	return _create_issue(get_property_context(property), subject, description)


@frappe.whitelist()
def get_support_issue(issue: str) -> dict:
	"""Return one support ticket and its conversation timeline.

	Args:
		issue: ``Issue`` name.

	Returns:
		Dict with ``issue`` and ``timeline``.

	Raises:
		frappe.PermissionError: When the ticket belongs to another Customer.
	"""
	doc = get_own_issue(issue)
	return {"issue": issue_detail(doc), "timeline": get_issue_timeline(doc)}


@frappe.whitelist(methods=["POST"])
def reply_to_support_issue(issue: str, message: str) -> dict:
	"""Add a customer reply to a support ticket.

	Args:
		issue: ``Issue`` name.
		message: Reply text from the customer.

	Returns:
		The new comment name and the refreshed ticket timeline.

	Raises:
		frappe.PermissionError: When the ticket belongs to another Customer.
		frappe.ValidationError: When the reply is empty or too long.
	"""
	doc = get_own_issue(issue)
	user = require_authenticated_user()
	message = _validated_reply(message)

	comment = frappe.get_doc(
		{
			"doctype": "Comment",
			"comment_type": "Comment",
			"reference_doctype": ISSUE_DOCTYPE,
			"reference_name": doc.name,
			"comment_email": user,
			"comment_by": get_fullname(user),
			"content": message_html(message),
		}
	)
	comment.insert(ignore_permissions=True)

	return {"comment": comment.name, "timeline": get_issue_timeline(doc)}


def _support_payload(context: dict, issues: list[dict]) -> dict:
	"""Return the workspace payload shared by the booking and property pages."""
	return {
		"context": context,
		"issues": issues,
		"counts": issue_counts(issues),
	}


def _create_issue(context: dict, subject: str, description: str) -> dict:
	"""Insert a customer Issue from a resolved support context."""
	subject = _validated_subject(subject)
	description = _validated_description(description)
	user = require_authenticated_user()

	issue = frappe.get_doc(
		{
			"doctype": ISSUE_DOCTYPE,
			"naming_series": "ISS-.YYYY.-",
			"subject": subject,
			"description": message_html(description),
			"customer": context["customer"],
			"customer_name": context["customer_name"],
			"raised_by": user,
			"company": context["company"],
			"status": "Open",
			"opening_date": nowdate(),
			"via_customer_portal": 1,
			"utility_property": context["property"],
			"utility_service_request": context["service_request"],
		}
	)
	issue.insert(ignore_permissions=True)

	return {"issue": issue_detail(issue), "timeline": get_issue_timeline(issue)}


def _validated_subject(value: str | None) -> str:
	"""Return a trimmed subject or throw when it is too short or too long."""
	subject = (value or "").strip()
	if len(subject) < 3:
		frappe.throw(_("Give the request a subject of at least 3 characters."))
	if len(subject) > SUBJECT_MAX_LENGTH:
		frappe.throw(_("The subject cannot be longer than {0} characters.").format(SUBJECT_MAX_LENGTH))

	return subject


def _validated_description(value: str | None) -> str:
	"""Return a trimmed description or throw when it is too short or too long."""
	description = (value or "").strip()
	if len(message_text(description)) < 10:
		frappe.throw(_("Describe the issue in at least 10 characters."))
	if len(description) > MESSAGE_MAX_LENGTH:
		frappe.throw(_("The description cannot be longer than {0} characters.").format(MESSAGE_MAX_LENGTH))

	return description


def _validated_reply(value: str | None) -> str:
	"""Return a trimmed reply or throw when it is empty or too long."""
	reply = (value or "").strip()
	if not message_text(reply):
		frappe.throw(_("Write a reply before sending it."))
	if len(reply) > MESSAGE_MAX_LENGTH:
		frappe.throw(_("The reply cannot be longer than {0} characters.").format(MESSAGE_MAX_LENGTH))

	return reply
