"""Fiscal year handling for generated demo transactions.

Demo leases start up to twelve months in the past while invoices and Sales
Orders are posted on lease dates. A site may not have a Fiscal Year covering
those dates, and ERPNext blocks accounting documents outside an active Fiscal
Year. The helpers here keep generated documents inside the company's active
Fiscal Years and create the current year when the site has none at all.
"""

from datetime import date

import frappe
from erpnext.accounts.utils import FiscalYearError, get_fiscal_year
from frappe.utils import getdate, today

from .constants import DEMO_COMPANY

FISCAL_YEAR_CACHE_KEY = "fiscal_years"


def reset_fiscal_year_cache() -> None:
	"""Drop ERPNext's cached Fiscal Year list for all companies."""
	frappe.cache().delete_key(FISCAL_YEAR_CACHE_KEY)


def ensure_current_fiscal_year() -> None:
	"""Create the current calendar Fiscal Year when the demo company has none.

	Most sites already configure Fiscal Years. The demo only creates one when
	the company has no active year for today, so generated documents are not
	rejected by accounting validation.
	"""
	current = getdate(today())
	if _fiscal_year_for(current):
		return

	year = current.year
	if frappe.db.exists("Fiscal Year", str(year)):
		_link_company_to_fiscal_year(str(year))
	else:
		fiscal_year = frappe.new_doc("Fiscal Year")
		fiscal_year.year = str(year)
		fiscal_year.year_start_date = f"{year}-01-01"
		fiscal_year.year_end_date = f"{year}-12-31"
		fiscal_year.append("companies", {"company": DEMO_COMPANY})
		fiscal_year.insert(ignore_permissions=True)


def active_fiscal_date(value: str | date | None) -> date:
	"""Return ``value`` when it belongs to an active Fiscal Year.

	Dates outside every active Fiscal Year are moved to today, which is always
	covered by :func:`ensure_current_fiscal_year`.
	"""
	candidate = getdate(value or today())
	return candidate if _fiscal_year_for(candidate) else getdate(today())


def _fiscal_year_for(value: date):
	"""Return the active Fiscal Year covering ``value`` for the demo company."""
	try:
		return get_fiscal_year(value, company=DEMO_COMPANY, verbose=0)
	except FiscalYearError:
		return None


def _link_company_to_fiscal_year(fiscal_year: str) -> None:
	"""Add the demo company to an existing Fiscal Year named after the year."""
	doc = frappe.get_doc("Fiscal Year", fiscal_year)
	if any(row.company == DEMO_COMPANY for row in doc.companies):
		return

	doc.append("companies", {"company": DEMO_COMPANY})
	doc.save(ignore_permissions=True)
