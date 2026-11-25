import frappe
from frappe import _
from frappe.model.document import Document

from ...utils.request_link import check_request_customer


def validate(doc: Document, method: str) -> None:
	check_request_customer(doc)
	check_meter_not_held(doc)


def check_meter_not_held(doc: Document) -> None:
	"""Refuse to close a claim while its meter is on another customer's Closed claim.

	Only when the claim becomes Closed, or its serial or customer changes while
	Closed: existing records already have meters on several Closed claims.
	"""
	if doc.status != "Closed" or not doc.serial_no:
		return
	if not any(doc.has_value_changed(field) for field in ("status", "serial_no", "customer")):
		return

	other = frappe.db.get_value(
		"Warranty Claim",
		{
			"serial_no": doc.serial_no,
			"status": "Closed",
			"customer": ("!=", doc.customer),
			"name": ("!=", doc.name),
		},
		["name", "customer"],
		as_dict=True,
		order_by="creation desc",
	)
	if other:
		frappe.throw(
			_(
				"Meter {0} is still on Closed Warranty Claim {1} of customer {2}. "
				"Disconnect it there, which reopens that claim, before closing this one."
			).format(doc.serial_no, other.name, other.customer),
			title=_("Meter Installed Elsewhere"),
		)
