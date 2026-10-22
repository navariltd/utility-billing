"""Deferred posting of Sales Invoice lines.

Utility customers are billed in advance for periods starting after the invoice
date. Instead of crediting the income account of such a line on the invoice
posting date, the revenue is parked in the deferred account configured for the
company and is moved to the real income account by a Journal Entry dated the
Deferred Posting Date of the line.

The feature flag and the deferred account of each company live in
``Utility Billing Settings``. The Deferred Posting Date is stored on
``Sales Invoice Item`` in ``custom_posting_date`` and the journal entry created
for the line is stored in ``custom_deferred_journal_entry``. A line whose
Deferred Posting Date is set while the feature is switched off simply posts to
its income account.

A line without a Deferred Posting Date follows the invoice posting date: the
first line of an item posts with the invoice and every further line of the same
item one month later, so an invoice covering several periods recognises each
period on its own date while a line posting on the invoice date itself is not
deferred at all.

The journal entry is booked as an ERPNext ``Deferred Revenue`` voucher: only such
a voucher may reference the invoice from its rows, and it never touches the
outstanding amount of the invoice.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import TYPE_CHECKING

import frappe
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
)
from erpnext.accounts.utils import get_account_currency
from frappe import _
from frappe.utils import add_months, flt, getdate

if TYPE_CHECKING:
	from frappe.model.document import Document

SETTINGS_DOCTYPE = "Utility Billing Settings"
DEFERRED_ACCOUNTS_FIELD = "deferred_accounts"
ENABLE_FIELD = "enable_deferred_posting"

INVOICE_ITEM_DOCTYPE = "Sales Invoice Item"
DEFERRED_ACCOUNT_FIELD = "custom_deferred_account"
DEFERRED_REVENUE_ACCOUNT_FIELD = "deferred_revenue_account"

JOURNAL_ENTRY_DOCTYPE = "Journal Entry"
JOURNAL_ENTRY_ACCOUNT_DOCTYPE = "Journal Entry Account"
JOURNAL_ENTRY_VOUCHER_TYPE = "Deferred Revenue"

POSTING_DATE_FIELD = "custom_posting_date"
JOURNAL_ENTRY_FIELD = "custom_deferred_journal_entry"


def is_deferred_posting_enabled() -> bool:
	"""Return whether deferred posting is enabled in the Utility Billing Settings."""
	return bool(frappe.db.get_single_value(SETTINGS_DOCTYPE, ENABLE_FIELD))


def get_deferred_account(company: str) -> str | None:
	"""Return the deferred account configured for a company.

	Args:
		company: Company whose deferred account is looked up.

	Returns:
		The deferred account name, or None when the company has no mapping.
	"""
	for row in frappe.get_cached_doc(SETTINGS_DOCTYPE).get(DEFERRED_ACCOUNTS_FIELD) or []:
		if row.company == company and row.deferred_account:
			return row.deferred_account

	return None


def is_deferred_line(doc: Document, item) -> bool:
	"""Return whether the revenue of a Sales Invoice line is deferred.

	A line is deferred when deferred posting is enabled and the line posts after
	the invoice, so a line posting on the invoice date itself, a credit note, an
	internal transfer and a line without a Deferred Posting Date all keep the
	standard posting.

	Args:
		doc: Sales Invoice being posted.
		item: Sales Invoice Item row.

	Returns:
		True when the revenue of the line has to be parked in the deferred account.
	"""
	if not item.get(POSTING_DATE_FIELD) or _keeps_standard_posting(doc):
		return False

	if not is_deferred_posting_enabled():
		return False

	return getdate(item.get(POSTING_DATE_FIELD)) > getdate(doc.posting_date)


def fill_posting_dates(doc: Document) -> None:
	"""Fill the Deferred Posting Date of the invoice lines that have none.

	The first line of an item posts with the invoice, every further line of the
	same item posts one month later, so an invoice covering several periods of an
	item recognises each period on its own date. A date that was set by hand is
	kept.

	Args:
		doc: Sales Invoice being validated.
	"""
	rows = doc.get("items") or []

	for row, posting_date in zip(rows, resolve_posting_dates(doc.posting_date, rows)):
		if posting_date:
			row.set(POSTING_DATE_FIELD, posting_date)


def resolve_posting_dates(posting_date: str, rows: list) -> list[str | None]:
	"""Return the Deferred Posting Date to fill on each invoice line.

	The n-th line of an item defaults to the invoice Posting Date plus n-1
	months. Lines that already carry a date keep it and still count towards the
	sequence of their item.

	Args:
		posting_date: Posting Date of the Sales Invoice.
		rows: Invoice lines, as documents or dictionaries.

	Returns:
		One entry per row, holding the date to fill in, or None when the row has
		no item or already carries a date.
	"""
	seen: dict[str, int] = {}
	dates: list[str | None] = []

	for row in rows:
		item_code = row.get("item_code")
		if not item_code:
			dates.append(None)
			continue

		index = seen.get(item_code, 0)
		seen[item_code] = index + 1

		dates.append(None if row.get(POSTING_DATE_FIELD) else str(add_months(posting_date, index)))

	return dates


def validate_deferred_lines(doc: Document) -> None:
	"""Validate the deferred lines of a Sales Invoice and tag their deferred account.

	Lines of an invoice keep the standard posting when deferred posting is
	switched off, so a Deferred Posting Date left on them is harmless.

	Args:
		doc: Sales Invoice being validated.

	Raises:
		frappe.ValidationError: when a Deferred Posting Date precedes the invoice
			Posting Date, when the line also relies on the ERPNext Deferred
			Revenue feature, or when no deferred account is configured for a
			company whose invoice has lines posting later.
	"""
	if _keeps_standard_posting(doc) or not is_deferred_posting_enabled():
		return

	lines = [item for item in doc.get("items") or [] if item.get(POSTING_DATE_FIELD)]
	if not lines:
		return

	for item in lines:
		if item.get("enable_deferred_revenue"):
			frappe.throw(
				_("Row #{0}: Deferred Posting Date cannot be combined with Deferred Revenue.").format(
					item.idx
				)
			)

		if getdate(item.get(POSTING_DATE_FIELD)) < getdate(doc.posting_date):
			frappe.throw(
				_("Row #{0}: Deferred Posting Date cannot be before the Posting Date of the invoice.").format(
					item.idx
				)
			)

	deferred_account = get_deferred_account(doc.company)
	if not deferred_account and any(is_deferred_line(doc, item) for item in lines):
		frappe.throw(
			_("Set the deferred account of company {0} in {1}.").format(
				frappe.bold(doc.company), frappe.bold(_(SETTINGS_DOCTYPE))
			)
		)

	for item in doc.get("items") or []:
		if item.get("enable_deferred_revenue"):
			continue  # ERPNext keeps the deferred account of such a line itself

		# The deferred account of the company is shown on every line that parks
		# its revenue, and ERPNext needs it on the line as well so that the
		# journal entry may reference the invoice from its rows.
		account = deferred_account if is_deferred_line(doc, item) else None
		item.set(DEFERRED_ACCOUNT_FIELD, account)

		if account:
			item.set(DEFERRED_REVENUE_ACCOUNT_FIELD, account)


def _keeps_standard_posting(doc: Document) -> bool:
	"""Return whether an invoice must be excluded from deferred posting."""
	if doc.is_return:
		return True

	is_internal_transfer = getattr(doc, "is_internal_transfer", None)
	return bool(is_internal_transfer and is_internal_transfer())


@contextmanager
def deferred_income_accounts(doc: Document) -> Iterator[None]:
	"""Credit the deferred account instead of the income account of a line.

	ERPNext builds the income GL entries of an invoice from ``item.income_account``.
	Swapping the account while the GL entries are built credits the deferred
	account while the invoice line keeps its real income account.

	Args:
		doc: Sales Invoice whose GL entries are being built.
	"""
	swapped: list[tuple] = []
	try:
		if any(is_deferred_line(doc, item) for item in doc.get("items") or []):
			deferred_account = get_deferred_account(doc.company)
			for item in doc.get("items") or []:
				if (
					deferred_account
					and is_deferred_line(doc, item)
					and item.income_account != deferred_account
				):
					swapped.append((item, item.income_account))
					item.income_account = deferred_account

		yield
	finally:
		for item, income_account in swapped:
			item.income_account = income_account


def create_deferred_journal_entries(doc: Document) -> list[str]:
	"""Post the deferred revenue of a Sales Invoice to the income accounts.

	One Journal Entry is created per Deferred Posting Date, holding the deferred
	account and income account rows of every deferred line sharing that date.

	Args:
		doc: Submitted Sales Invoice.

	Returns:
		Names of the submitted Journal Entries.
	"""
	deferred_account = get_deferred_account(doc.company)
	if not deferred_account:
		return []

	created = []
	for posting_date, items in _lines_by_posting_date(doc).items():
		journal_entry = _build_journal_entry(doc, posting_date, items, deferred_account)
		if not journal_entry.accounts:
			continue

		journal_entry.insert(ignore_permissions=True)
		journal_entry.submit()
		_link_lines(items, journal_entry.name)
		created.append(journal_entry.name)

	return created


def cancel_deferred_journal_entries(doc: Document) -> list[str]:
	"""Cancel the Journal Entries that recognised the deferred revenue.

	Called when the Sales Invoice is cancelled so that the deferred account is
	cleared together with the invoice GL entries.

	Args:
		doc: Sales Invoice being cancelled.

	Returns:
		Names of the cancelled Journal Entries.
	"""
	cancelled = []
	for item in doc.get("items") or []:
		journal_entry = item.get(JOURNAL_ENTRY_FIELD)
		if not journal_entry or not _is_booked_by_live_journal_entry(item):
			continue

		frappe.get_doc(JOURNAL_ENTRY_DOCTYPE, journal_entry).cancel()
		cancelled.append(journal_entry)

	return cancelled


def _lines_by_posting_date(doc: Document) -> dict[str, list]:
	"""Group the deferred lines of an invoice by their Deferred Posting Date."""
	lines: dict[str, list] = {}
	for item in doc.get("items") or []:
		if not flt(item.base_net_amount) or not is_deferred_line(doc, item):
			continue

		if _is_booked_by_live_journal_entry(item):
			continue

		lines.setdefault(str(getdate(item.get(POSTING_DATE_FIELD))), []).append(item)

	return lines


def _is_booked_by_live_journal_entry(item) -> bool:
	"""Return whether the line is already recognised by a live Journal Entry.

	Guards against double booking when the invoice is posted again, for example
	after an amendment copied the Journal Entry reference of the original line.
	"""
	journal_entry = item.get(JOURNAL_ENTRY_FIELD)
	if not journal_entry or frappe.db.get_value(JOURNAL_ENTRY_DOCTYPE, journal_entry, "docstatus") != 1:
		return False

	return bool(
		frappe.db.exists(
			JOURNAL_ENTRY_ACCOUNT_DOCTYPE,
			{"parent": journal_entry, "reference_detail_no": item.name},
		)
	)


def _build_journal_entry(doc: Document, posting_date: str, items: list, deferred_account: str):
	"""Build the Journal Entry that moves deferred revenue to the income accounts.

	The voucher is booked as a ``Deferred Revenue`` entry, the only voucher type
	whose rows ERPNext lets reference the invoice; the rows of such a voucher are
	not part of the outstanding amount of the invoice.

	Args:
		doc: Submitted Sales Invoice.
		posting_date: Date the revenue is recognised on.
		items: Deferred lines sharing ``posting_date``.
		deferred_account: Deferred account of the company.

	Returns:
		An unsaved Journal Entry.
	"""
	journal_entry = frappe.new_doc(JOURNAL_ENTRY_DOCTYPE)
	journal_entry.voucher_type = JOURNAL_ENTRY_VOUCHER_TYPE
	journal_entry.company = doc.company
	journal_entry.posting_date = posting_date
	journal_entry.user_remark = _("Deferred revenue of {0} {1}").format(_(doc.doctype), doc.name)

	deferred_currency = get_account_currency(deferred_account)

	for item in items:
		base_amount = flt(item.base_net_amount)
		income_currency = get_account_currency(item.income_account)

		rows = (
			{
				"account": deferred_account,
				"account_currency": deferred_currency,
				"debit": base_amount,
				"debit_in_account_currency": _amount_in_account_currency(doc, item, deferred_currency),
			},
			{
				"account": item.income_account,
				"account_currency": income_currency,
				"credit": base_amount,
				"credit_in_account_currency": _amount_in_account_currency(doc, item, income_currency),
			},
		)

		for row in rows:
			row.update(_line_references(doc, item))
			journal_entry.append("accounts", row)

	return journal_entry


def _line_references(doc: Document, item) -> dict:
	"""Return the references and accounting dimensions of an invoice line.

	The rows reference the invoice itself through ``reference_type`` and
	``reference_name`` and identify the line through ``reference_detail_no``.
	ERPNext accepts such a reference when the row books the deferred account or
	the income account stored on the line, which is why both are kept on it.
	"""
	references = {
		"cost_center": item.cost_center,
		"project": item.project or doc.project,
		"reference_type": doc.doctype,
		"reference_name": doc.name,
		"reference_detail_no": item.name,
	}

	for dimension in get_accounting_dimensions():
		references[dimension] = item.get(dimension)

	return references


def _amount_in_account_currency(doc: Document, item, account_currency: str) -> float:
	"""Return a line amount expressed in the currency of an account.

	Mirrors the amounts ERPNext posts in the invoice GL entries: accounts in the
	company currency carry the base amount, any other account carries the
	transaction amount.

	Args:
		doc: Sales Invoice being posted.
		item: Sales Invoice Item row.
		account_currency: Currency of the account the amount is booked to.

	Returns:
		The amount in the currency of the account.
	"""
	if account_currency == doc.company_currency:
		return flt(item.base_net_amount)

	return flt(item.net_amount)


def _link_lines(items: list, journal_entry: str) -> None:
	"""Store the Journal Entry of a Deferred Posting Date on its invoice lines.

	The lines are updated in memory as well, so that a second submit or a
	cancellation in the same request sees the reference.
	"""
	for item in items:
		item.set(JOURNAL_ENTRY_FIELD, journal_entry)
		frappe.db.set_value(INVOICE_ITEM_DOCTYPE, item.name, JOURNAL_ENTRY_FIELD, journal_entry)
