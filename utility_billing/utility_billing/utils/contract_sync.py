"""Keep a request's Contracts in step with it, under the Item Price approach.

A Contract copies its request's dates and property rows when it is made, and
the Contract's copy is locked. When a submitted request's dates or rows change
afterwards, the change is saved only with the user's consent to update its
Contracts too, so the Contract never goes stale: either both change, or the
request change is refused.

Consent is the ``__update_contract`` key of the saved document. The form sets
it when the user answers yes to "Update the Contract to match?"; an API call
has to send it explicitly. Data Import never does, so its changes are refused.

The request's own checks (row dates inside its dates, overlapping leases, lease
moves) run before this one, and everything runs in one transaction, so a
refused or failed save leaves the Contracts untouched.

Nothing here applies under Auto Repeat.
"""

import frappe
from frappe import _
from frappe.model import no_value_fields
from frappe.utils import cint, getdate

from utility_billing.utility_billing.utils.request_prices import is_item_price_approach

REQUEST_DOCTYPE = "Utility Service Request"
ROW_DOCTYPE = "Contract Utility Property Item"
CONSENT_KEY = "__update_contract"
HEADER_FIELDS = ("start_date", "end_date")
DATE_FIELDS = {"start_date", "end_date"}
# Not copied: a row released on the Contract stays released
SKIPPED_ROW_FIELDS = {"is_active"}


def _date(value):
	return getdate(value) if value else None


def contract_terms(doc) -> tuple:
	"""Return what a Contract copies from its request: the dates and the property rows."""
	header = tuple(_date(doc.get(fieldname)) for fieldname in HEADER_FIELDS)
	rows = sorted(
		(
			row.utility_property,
			_date(row.start_date),
			_date(row.end_date),
			cint(row.get("is_active")),
		)
		for row in doc.get("requested_properties") or []
		if row.utility_property
	)

	return header, tuple(rows)


def contract_terms_changed(doc, before) -> bool:
	"""Return whether a request's dates or property rows differ from its saved version."""
	return bool(before) and contract_terms(doc) != contract_terms(before)


def linked_contracts(service_request: str) -> list[str]:
	"""Return the request's Contracts that are not cancelled, drafts included."""
	return frappe.get_all(
		"Contract",
		filters={"utility_service_request": service_request, "docstatus": ("<", 2)},
		pluck="name",
		order_by="creation asc",
	)


def contracts_to_update(doc, before) -> list[str]:
	"""Return the Contracts a request change has to update, under Item Price only."""
	if not (is_item_price_approach() and contract_terms_changed(doc, before)):
		return []

	return linked_contracts(doc.name)


def refuse_unconfirmed_contract_change(doc, before) -> None:
	"""Refuse a request change that would leave its Contracts stale.

	Runs from the request's before_update_after_submit, after its own checks.

	Raises:
		frappe.ValidationError: When the dates or rows changed, the request has
			a Contract, and the save does not carry the user's consent.
	"""
	names = contracts_to_update(doc, before)
	if not names or cint(doc.get(CONSENT_KEY)):
		return

	frappe.throw(
		_(
			"Utility Service Request {0} has Contract {1}. Its dates and properties follow the "
			"request, so confirm updating the Contract to save this change."
		).format(frappe.bold(doc.name), ", ".join(frappe.bold(name) for name in names)),
		title=_("Contract not updated"),
	)


def sync_contracts(doc, before) -> None:
	"""Copy a request's dates and property rows to its Contracts.

	Runs from the request's on_update_after_submit. Rows are matched by
	property: a new property is added, and a row removed or unticked on the
	request is released on the Contract, never deleted. A row released on the
	Contract stays released.

	The Contract is saved normally, so ERPNext sets its status from the new
	dates, the Contract hooks set property statuses and a Version records the
	change. Two flags let the change through, both server only: Frappe's
	``ignore_validate_update_after_submit`` for the dates and rows that do not
	allow edits after submit, and ``from_service_request`` for the Contract's
	own lock. A draft may still lack its Contract Terms, so mandatory fields are
	not checked on a draft.
	"""
	for name in contracts_to_update(doc, before):
		contract = frappe.get_doc("Contract", name)
		contract.start_date = _date(doc.start_date)
		contract.end_date = _date(doc.end_date)

		rows = {row.utility_property: row for row in contract.get("properties") or []}
		kept = set()
		for source in doc.get("requested_properties") or []:
			if not source.utility_property:
				continue

			kept.add(source.utility_property)
			target = rows.get(source.utility_property)
			if not target:
				target = contract.append("properties", {"is_active": 1})
			copy_row(source, target)
			if not cint(source.get("is_active")):
				target.is_active = 0

		for row in contract.get("properties") or []:
			if row.utility_property not in kept:
				row.is_active = 0

		contract.flags.from_service_request = True
		contract.flags.ignore_validate_update_after_submit = True
		contract.flags.ignore_mandatory = contract.docstatus == 0
		contract.save(ignore_permissions=True)


def copy_row(source, target) -> None:
	"""Copy a request's property row onto a Contract row, Is Active aside."""
	for df in frappe.get_meta(ROW_DOCTYPE).fields:
		if df.fieldtype in no_value_fields or df.fieldname in SKIPPED_ROW_FIELDS:
			continue

		value = source.get(df.fieldname)
		target.set(df.fieldname, _date(value) if df.fieldname in DATE_FIELDS else value)


@frappe.whitelist()
def get_contracts_to_update(doc: dict | str) -> list[str]:
	"""Return the Contracts the form has to ask about before saving a submitted request.

	Args:
		doc: The request as it is in the form.

	Returns:
		The Contracts that would change, empty when nothing needs asking.
	"""
	doc = frappe.get_doc(frappe.parse_json(doc) if isinstance(doc, str) else doc)
	if doc.doctype != REQUEST_DOCTYPE or doc.docstatus != 1 or doc.is_new():
		return []

	doc.check_permission("write")

	return contracts_to_update(doc, frappe.get_doc(REQUEST_DOCTYPE, doc.name))
