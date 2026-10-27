"""Rent Sales Orders and Sales Invoices for the demo tenancies.

The generated documents follow the site's configured billing approach. An
``Item Price`` site receives one invoice per leased property priced from the
generated schedule. An ``Auto Repeat`` site receives a submitted anchor
invoice per property plus the Auto Repeat that will copy it.
"""

import frappe
from frappe.utils import add_days, flt, getdate, today

from utility_billing.utility_billing.doctype.utility_service_request.utility_service_request import (
	create_sales_invoice_doc,
	create_sales_order_doc,
)
from utility_billing.utility_billing.utils.item_rate import get_rate_for_date
from utility_billing.utility_billing.utils.service_item import ensure_service_item

from .constants import DEMO_COMPANY
from .fiscal import active_fiscal_date
from .pricing import load_rent_rates
from .utils import logger

DUE_AFTER_DAYS = 10
TRANSACTION_SAVEPOINT = "demo_rent_transaction"


def create_demo_transactions(service_request_names: list[str]) -> None:
	"""Create rent Sales Orders and Sales Invoices for signed demo leases.

	Args:
	    service_request_names: Demo ``Utility Service Request`` names.
	"""
	settings = frappe.get_cached_doc("Utility Billing Settings")
	approach = settings.rent_billing_approach or "Auto Repeat"
	base_rents = load_rent_rates()

	for name in service_request_names:
		request = frappe.get_doc("Utility Service Request", name)
		if request.company != DEMO_COMPANY or not _is_signed_tenant(request):
			continue

		frappe.db.savepoint(TRANSACTION_SAVEPOINT)
		try:
			_create_sales_order(request, base_rents, settings)
			for row in request.get("requested_properties") or []:
				_create_sales_invoice(request, row, base_rents, settings, approach)
		except Exception:
			frappe.db.rollback(save_point=TRANSACTION_SAVEPOINT)
			logger.exception(f"Could not create demo transactions for {name}")


def _is_signed_tenant(request) -> bool:
	"""Return whether the request has a submitted, signed Contract."""
	contract = frappe.get_all(
		"Contract",
		filters={
			"utility_service_request": request.name,
			"docstatus": 1,
			"is_signed": 1,
		},
		pluck="name",
		order_by="creation desc",
		limit=1,
	)

	return bool(contract)


def _create_sales_order(request, base_rents: dict, settings) -> str | None:
	"""Create one rent Sales Order for the request when none exists yet."""
	if frappe.db.exists("Sales Order", {"utility_service_request": request.name, "docstatus": ("<", 2)}):
		return None

	transaction_date = active_fiscal_date(request.start_date or today())
	items = [
		_invoice_item(request, row, base_rents, transaction_date)
		for row in request.get("requested_properties") or []
		if row.utility_property
	]
	if not items:
		return None

	name = create_sales_order_doc(
		request.name,
		items,
		customer=request.customer,
		customer_name=request.customer_name,
		transaction_date=str(transaction_date),
		company=request.company,
	)

	if settings.sales_order_creation_state == "Submitted":
		frappe.get_doc("Sales Order", name).submit()

	return name


def _create_sales_invoice(request, row, base_rents: dict, settings, approach: str) -> str | None:
	"""Create the first rent invoice of one property when none exists yet."""
	property_name = row.utility_property
	if not property_name:
		return None

	item_code = ensure_service_item(property_name)
	if item_code and _property_already_invoiced(request.name, item_code):
		return None

	posting_date = _invoice_posting_date(row, request)
	items = [_invoice_item(request, row, base_rents, posting_date)]
	name = create_sales_invoice_doc(
		request.name,
		items,
		customer=request.customer,
		customer_name=request.customer_name,
		posting_date=str(posting_date),
		due_date=str(add_days(posting_date, DUE_AFTER_DAYS)),
		company=request.company,
		property=property_name,
		enable_auto_repeat="1" if approach == "Auto Repeat" else None,
		adjustment_rule=row.adjustment_rule if approach == "Auto Repeat" else None,
		start_date=_date_string(_auto_repeat_start(row, approach)),
		end_date=_date_string(row.end_date),
	)

	if approach == "Auto Repeat" or settings.sales_invoice_creation_state == "Submitted":
		frappe.get_doc("Sales Invoice", name).submit()

	return name


def _auto_repeat_start(row, approach: str):
	"""Start a demo Auto Repeat today when its lease started in the past."""
	if approach != "Auto Repeat":
		return row.start_date

	start = getdate(row.start_date or today())
	return max(start, getdate(today()))


def _date_string(value) -> str | None:
	"""Return a date as the string expected by the service request APIs."""
	return str(getdate(value)) if value else None


def _invoice_posting_date(row, request):
	"""Return today, or the lease start when the lease has not begun yet."""
	start = getdate(row.start_date or request.start_date or today())
	end = getdate(row.end_date or request.end_date) if (row.end_date or request.end_date) else None
	current = getdate(today())

	if current < start:
		return active_fiscal_date(start)
	if end and current > end:
		return active_fiscal_date(start)

	return active_fiscal_date(current)


def _property_already_invoiced(service_request: str, item_code: str) -> bool:
	"""Return whether the request already has an invoice for a property item."""
	invoices = frappe.get_all(
		"Sales Invoice",
		filters={"utility_service_request": service_request, "docstatus": ("<", 2)},
		pluck="name",
	)
	if not invoices:
		return False

	return bool(
		frappe.get_all(
			"Sales Invoice Item",
			filters={"parent": ("in", invoices), "item_code": item_code},
			pluck="name",
			limit=1,
		)
	)


def _invoice_item(request, row, base_rents: dict, billing_date) -> dict:
	"""Build the rent item row of a property for a billing date."""
	item_code = ensure_service_item(row.utility_property)
	if not item_code:
		raise ValueError(f"{row.utility_property} has no service item.")

	item = frappe.get_cached_doc("Item", item_code)
	rate = get_rate_for_date(
		item_code,
		billing_date,
		customer=request.customer,
		price_list=request.price_list,
		uom=item.stock_uom,
		qty=1,
	)
	if rate is None:
		rate = flt(base_rents.get(row.utility_property))

	return {
		"item_code": item_code,
		"item_name": item.item_name,
		"qty": 1,
		"uom": item.stock_uom,
		"stock_uom": item.stock_uom,
		"conversion_factor": 1,
		"rate": rate,
		"amount": rate,
		"delivery_date": str(billing_date or today()),
	}
