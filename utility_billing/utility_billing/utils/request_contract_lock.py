"""Lock a request's Contract terms once it has a Contract, under the Item Price approach.

A Contract copies its request's dates and property rows when it is made, and
the Contract's copy is locked (``overrides.server.contract.check_rows_unchanged``).
So the request's own copy is locked too: while it has a Contract that is not
cancelled, its dates, contract length and property rows cannot change. To change
them, cancel the Contract, or delete a draft one, or create a new request.

Runs on every save of the request (form, REST, Data Import, the portal), from
validate for a draft request, which can have a Contract too, and from
before_update_after_submit for a submitted one.

Nothing here applies under Auto Repeat.
"""

import frappe
from frappe import _
from frappe.model import no_value_fields
from frappe.utils import cint, flt, getdate

from utility_billing.utility_billing.utils.request_prices import is_item_price_approach

ROW_DOCTYPE = "Contract Utility Property Item"
HEADER_FIELDS = ("start_date", "end_date", "contract_length_months")


def normalise(fieldtype: str, value):
	"""Return a value in one form, whether read from the database or a form."""
	if fieldtype == "Date":
		return getdate(value) if value else None
	if fieldtype in ("Check", "Int"):
		return cint(value)
	if fieldtype in ("Float", "Currency", "Percent"):
		return flt(value)

	return value or None


def value_fields(doctype: str) -> list:
	return [df for df in frappe.get_meta(doctype).fields if df.fieldtype not in no_value_fields]


def contract_terms(doc) -> tuple:
	"""Return what a Contract copies from its request: the dates and every property row.

	Rows are compared by their values, not their names, so rows removed and
	added again unchanged (as Data Import may do) are no change.
	"""
	meta = frappe.get_meta(doc.doctype)
	header = tuple(normalise(meta.get_field(fieldname).fieldtype, doc.get(fieldname)) for fieldname in HEADER_FIELDS)
	fields = value_fields(ROW_DOCTYPE)
	rows = sorted(
		(tuple(str(normalise(df.fieldtype, row.get(df.fieldname))) for df in fields))
		for row in doc.get("requested_properties") or []
	)

	return header, tuple(rows)


def request_contracts(service_request: str) -> tuple[list[str], list[str]]:
	"""Return the request's submitted and draft Contracts. Cancelled ones count as none."""
	contracts = frappe.get_all(
		"Contract",
		filters={"utility_service_request": service_request, "docstatus": ("<", 2)},
		fields=["name", "docstatus"],
		order_by="creation asc",
	)

	return (
		[row.name for row in contracts if row.docstatus == 1],
		[row.name for row in contracts if row.docstatus == 0],
	)


def check_contract_terms_locked(doc) -> None:
	"""Refuse a change to the dates, contract length or property rows of a request with a Contract.

	Raises:
		frappe.ValidationError: Naming the Contract, submitted first.
	"""
	if doc.is_new() or not is_item_price_approach():
		return

	before = doc.get_doc_before_save()
	if not before or contract_terms(doc) == contract_terms(before):
		return

	submitted, drafts = request_contracts(doc.name)
	if submitted:
		frappe.throw(
			_("This request has Contract {0}. Cancel the Contract, or create a new request.").format(
				", ".join(frappe.bold(name) for name in submitted)
			),
			title=_("Request locked by its Contract"),
		)

	if drafts:
		frappe.throw(
			_("This request has draft Contract {0}. Delete it or submit it first.").format(
				", ".join(frappe.bold(name) for name in drafts)
			),
			title=_("Request locked by its Contract"),
		)
