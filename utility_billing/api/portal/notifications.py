"""Portal notifications for bookings and outstanding payments.

Notifications are standard ``Notification Log`` records, which the portal
already lists through ``frappe.desk.doctype.notification_log``. No email is sent
here: delivery preferences and outgoing mail stay with Frappe's own settings.
"""

import frappe
from frappe import _
from frappe.utils import add_days, fmt_money, formatdate, nowdate

BOOKING_LINK = "/rental-portal/bookings"
INVOICE_LINK = "/rental-portal/invoices"
REMINDER_INTERVAL_DAYS = 7


def notify_portal_user(
	user: str | None,
	title: str,
	subject: str,
	*,
	document_type: str | None = None,
	document_name: str | None = None,
	link: str | None = None,
) -> None:
	"""Create an in-app notification for a portal user.

	Args:
		user: Recipient user; ignored for guests and missing users.
		title: Short notification title.
		subject: Message body.
		document_type: Related doctype, when any.
		document_name: Related document, when any.
		link: Portal URL opened from the notification.
	"""
	if not user or user == "Guest" or not frappe.db.exists("User", user):
		return

	log = frappe.new_doc("Notification Log")
	log.update(
		{
			"type": _notification_type(),
			"title": title,
			"subject": subject,
			"for_user": user,
			"from_user": "Administrator",
			"document_type": document_type,
			"document_name": document_name,
			"link": link,
		}
	)
	log.flags.ignore_links = True
	log.insert(ignore_permissions=True)


def notify_booking_event(user: str, event: str, booking, **context) -> None:
	"""Notify a tenant about a booking lifecycle event.

	Args:
		user: Portal user to notify.
		event: One of ``requested``, ``confirmed``, ``modified``, ``cancelled``,
			``extended`` or ``renewed``.
		booking: ``Utility Service Request`` document or a dict with ``name``
			and a property label.
		context: Extra values used in the message (``end_date``, ``renewal``).
	"""
	name = booking.get("name")
	property_label = _booking_property(booking)
	templates = {
		"requested": (
			_("Booking request received"),
			_("Your booking request {0} for {1} was received and is awaiting confirmation."),
		),
		"confirmed": (
			_("Booking confirmed"),
			_("Your booking {0} for {1} has been confirmed."),
		),
		"modified": (
			_("Booking updated"),
			_("The dates of booking {0} for {1} were updated."),
		),
		"cancelled": (
			_("Booking cancelled"),
			_("Booking {0} for {1} has been cancelled."),
		),
		"extended": (
			_("Booking extended"),
			_("Booking {0} for {1} now runs until {2}."),
		),
		"renewed": (
			_("Renewal created"),
			_("Renewal {0} for {1} has been created."),
		),
	}
	title, template = templates.get(event, (_("Booking update"), _("Booking {0} was updated.")))
	subject = template.format(name, property_label, context.get("end_date") or "")

	notify_portal_user(
		user,
		title,
		subject,
		document_type="Utility Service Request",
		document_name=name,
		link=BOOKING_LINK,
	)


def send_payment_reminders() -> int:
	"""Notify portal customers of overdue, unpaid Sales Invoices.

	Each invoice is reminded about once every ``REMINDER_INTERVAL_DAYS`` days.

	Returns:
		Number of notifications created.
	"""
	portal_users = frappe.db.get_all(
		"Portal User",
		filters={"parenttype": "Customer"},
		fields=["parent", "user"],
	)
	if not portal_users:
		return 0

	users_by_customer: dict[str, list[str]] = {}
	for entry in portal_users:
		if entry.user and entry.user != "Guest":
			users_by_customer.setdefault(entry.parent, []).append(entry.user)

	invoices = frappe.db.get_all(
		"Sales Invoice",
		filters={
			"customer": ("in", list(users_by_customer)),
			"docstatus": 1,
			"outstanding_amount": (">", 0),
			"due_date": ("<", nowdate()),
		},
		fields=["name", "customer", "currency", "outstanding_amount", "due_date"],
		limit=500,
	)

	recent = frappe.db.get_all(
		"Notification Log",
		filters={
			"creation": (">", add_days(nowdate(), -REMINDER_INTERVAL_DAYS)),
			"document_type": "Sales Invoice",
		},
		fields=["for_user", "document_name"],
	)
	already_sent = {(row.for_user, row.document_name) for row in recent}

	created = 0
	for invoice in invoices:
		subject = _("Invoice {0} for {1} was due on {2}.").format(
			frappe.bold(invoice.name),
			fmt_money(invoice.outstanding_amount, currency=invoice.currency),
			formatdate(invoice.due_date),
		)
		for user in users_by_customer.get(invoice.customer, []):
			if (user, invoice.name) in already_sent:
				continue

			notify_portal_user(
				user,
				_("Payment reminder"),
				subject,
				document_type="Sales Invoice",
				document_name=invoice.name,
				link=INVOICE_LINK,
			)
			created += 1

	return created


def _notification_type() -> str | None:
	"""Return an existing Notification Type, if the site defines one."""
	if frappe.db.exists("Notification Type", "Alert"):
		return "Alert"

	return frappe.db.get_value("Notification Type", {}, "name", order_by="creation asc")


def _booking_property(booking) -> str:
	"""Return a property label from a request document or dict."""
	rows = booking.get("requested_properties") or []
	if rows:
		return rows[0].get("utility_property") or rows[0].get("property_name") or ""

	return booking.get("utility_property") or ""
