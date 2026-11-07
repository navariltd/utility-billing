"""Status of the Contracts made from a Utility Service Request, under the Item Price approach.

A Contract whose every property row is released (Is Active unticked) holds no
property any more, so it is Inactive. ERPNext sets a Contract's status from its
dates only: on every save of a submitted Contract, and daily through
``update_status_for_contracts``, which writes the status directly so no Contract
hook runs. This module keeps released Contracts Inactive against both, and
decides whether Require Contract still allows a request to be billed.

Only the status is written here. Properties are freed by the Contract hooks
(unticking a row, cancelling) and by ``release_ended_leases``.

Nothing here applies under Auto Repeat.
"""

import frappe
from frappe.query_builder.functions import Max
from frappe.utils import cint, getdate, nowdate

from utility_billing.utility_billing.utils.request_prices import is_item_price_approach

ROW_DOCTYPE = "Contract Utility Property Item"
INACTIVE = "Inactive"

# ERPNext's daily job that sets every signed Contract's status from its dates.
ERPNEXT_STATUS_JOB = "erpnext.crm.doctype.contract.contract.update_status_for_contracts"
ERPNEXT_STATUS_JOB_ENDING = ".update_status_for_contracts"


def all_rows_released(doc) -> bool:
	"""Return whether every property row of a Contract document is released."""
	rows = [row for row in doc.get("properties") or [] if row.utility_property]

	return bool(rows) and not any(cint(row.is_active) for row in rows)


def contract_released(contract_name: str) -> bool:
	"""Return whether every property row of a saved Contract is released."""
	rows = frappe.get_all(
		ROW_DOCTYPE,
		filters={"parent": contract_name, "parenttype": "Contract", "utility_property": ("is", "set")},
		pluck="is_active",
	)

	return bool(rows) and not any(cint(value) for value in rows)


def set_inactive_when_released(doc) -> None:
	"""Make a submitted Contract Inactive once every property row is released.

	Runs from the Contract's before_update_after_submit hook, after ERPNext's
	own, which sets the status from the dates, so the save that releases the
	last row leaves the Contract Inactive. A Contract with an active row keeps
	the status ERPNext gives it.
	"""
	if is_item_price_approach() and all_rows_released(doc):
		doc.status = INACTIVE


def released_property_status(doc, entry) -> str:
	"""Return the status a property takes when its Contract row stops holding it.

	Under Item Price, an active row whose Contract starts in the future still
	holds the property for that lease, so it is Reserved, as a Contract
	submitted with a future start leaves it. Otherwise the property is Available.
	"""
	if (
		is_item_price_approach()
		and cint(entry.is_active)
		and doc.start_date
		and getdate(doc.start_date) > getdate(nowdate())
	):
		return "Reserved"

	return "Available"


def contract_requirement_blocks(service_request: str) -> bool:
	"""Return whether Require Contract stops billing a request, under Item Price only.

	The daily Item Price job inserts its drafts without validation, so it checks
	here what ``check_service_request_contract`` checks when an invoice is saved:
	a submitted Contract, signed when signing is required. A Contract that has
	released every property is not refused outright: the job compares each
	billing date with the row's Released On instead (see ``release``).

	Args:
		service_request: ``Utility Service Request`` name.

	Returns:
		``True`` when the request may not be billed. Always ``False`` when
		Require Contract is off or rent is billed by Auto Repeat.
	"""
	settings = frappe.get_cached_doc("Utility Billing Settings")
	if not (is_item_price_approach() and settings.require_contract_before_sales_invoice_creation):
		return False

	filters = {"utility_service_request": service_request, "docstatus": 1}
	if settings.require_signed_contract:
		filters["is_signed"] = 1
	names = frappe.get_all("Contract", filters=filters, pluck="name")

	return not names


def set_released_contracts_inactive() -> list[str]:
	"""Set every submitted Contract whose rows are all released back to Inactive.

	Writes the status only, without touching ``modified``, as ERPNext's job does.

	Returns:
		Names of the Contracts set Inactive.
	"""
	if not is_item_price_approach():
		return []

	contract = frappe.qb.DocType("Contract")
	row = frappe.qb.DocType(ROW_DOCTYPE)
	names = (
		frappe.qb.from_(contract)
		.join(row)
		.on((row.parent == contract.name) & (row.parenttype == "Contract"))
		.select(contract.name)
		.where(contract.docstatus == 1)
		.where(contract.status != INACTIVE)
		.where(row.utility_property.isnotnull())
		.where(row.utility_property != "")
		.groupby(contract.name)
		.having(Max(row.is_active) == 0)
	).run(pluck=True)

	for name in names:
		frappe.db.set_value("Contract", name, "status", INACTIVE, update_modified=False)

	return names


def is_erpnext_status_job(method: str | None = None, kwargs: dict | None = None) -> bool:
	"""Return whether a finished background job was ERPNext's Contract status job.

	A scheduled job runs as ``run_scheduled_job`` with the scheduled method in
	``job_type``; a job enqueued directly runs as the method itself. Matched by
	the full path and by the method name ending, so a module move in ERPNext
	still matches.
	"""
	candidates = [(kwargs or {}).get("job_type"), method]

	scheduled_job_type = (kwargs or {}).get("scheduled_job_type")
	if scheduled_job_type and not (kwargs or {}).get("job_type"):
		candidates.append(frappe.db.get_value("Scheduled Job Type", scheduled_job_type, "method"))

	return any(
		candidate and (candidate == ERPNEXT_STATUS_JOB or candidate.endswith(ERPNEXT_STATUS_JOB_ENDING))
		for candidate in candidates
	)


def after_scheduled_job(method: str | None = None, kwargs: dict | None = None, **_) -> None:
	"""after_job hook: keep released Contracts Inactive after ERPNext's status job.

	Frappe calls every after_job hook in the same worker once a job has
	committed, so this runs right after ``update_status_for_contracts`` and
	needs no timing. Frappe does not commit after job hooks, hence the commit
	here. A failure is logged and rolled back so it never breaks the job.
	"""
	try:
		if not is_erpnext_status_job(method, kwargs):
			return

		if set_released_contracts_inactive():
			frappe.db.commit()
	except Exception:
		frappe.db.rollback()
		frappe.log_error(title="Released Contracts not set Inactive")
