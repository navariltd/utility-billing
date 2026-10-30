"""Item Prices owned by a Utility Service Request, found by its lease window.

Item Price carries no link to the request. A request owns the Item Prices of
its properties' service items that are scoped to its customer and start inside
the property's lease window: the Requested Properties row dates, falling back
to the request's Contract dates. Submitted leases of one property never
overlap (see ``lease_overlap``), so a price's ``valid_from`` names exactly one
request.

That only holds while every price stays inside the window it starts in, so
schedules may not run past the lease end, and moving a lease after submit moves
its prices with it (see ``adjust_prices_to_window``). It also needs each
service item to belong to one property, which ``validate_unshared_service_items``
checks before anything is written or deleted.

Everything here applies to a request's primary (rent) items under the Item
Price approach only. Secondary utility items, meter items and Auto Repeat sites
are never touched.
"""

import frappe
from frappe import _
from frappe.utils import getdate

PRICE_FIELDS = [
	"name",
	"item_code",
	"customer",
	"price_list",
	"valid_from",
	"valid_upto",
	"price_list_rate",
]


def is_item_price_approach() -> bool:
	"""Return whether the site bills rent by Item Price, the only approach the window applies to."""
	from utility_billing.utility_billing.utils.item_price_scope import (
		is_item_price_approach as _is_item_price_approach,
	)

	return _is_item_price_approach()


def require_item_price_approach() -> None:
	"""Raise when the site does not bill rent by Item Price."""
	if not is_item_price_approach():
		frappe.throw(_("Item Prices of a Utility Service Request are only defined when rent is billed by Item Price."))


def require_submitted(service_request) -> None:
	"""Raise when the request is not submitted, the only state the Define action is offered in."""
	if service_request.docstatus != 1:
		frappe.throw(
			_("Submit Utility Service Request {0} before defining its Item Prices.").format(service_request.name)
		)


def active_rows(service_request) -> list:
	"""Return the Requested Properties rows that still hold their property.

	An inactive row has released its property, which another request may then
	lease for the same dates, so it owns no prices.
	"""
	return [
		row
		for row in service_request.get("requested_properties") or []
		if row.utility_property and row.get("is_active") != 0
	]


def lease_window(service_request, property_name: str) -> tuple:
	"""Return ``(start, end)`` of a property's lease on a request.

	The property's active Requested Properties row wins; the request's Contract
	dates are the fallback. ``end`` is ``None`` for an open ended lease.
	"""
	row = next((r for r in active_rows(service_request) if r.utility_property == property_name), None)
	start = (row and row.start_date) or service_request.start_date
	end = (row and row.end_date) or service_request.end_date

	return (getdate(start) if start else None, getdate(end) if end else None)


def require_customer(service_request) -> str:
	"""Return the request's customer, raising when it has none.

	Item Prices of a request are scoped to its customer, so prices cannot be
	defined, edited or read back until the request has one.
	"""
	if not service_request.get("customer"):
		frappe.throw(
			_("Set the Customer of Utility Service Request {0} before defining its Item Prices.").format(
				service_request.name
			)
		)

	return service_request.customer


def window_filters(service_request, property_name: str, item_code: str, window=None) -> list | None:
	"""Return Item Price filters for the prices a request owns for one property.

	Args:
		service_request: ``Utility Service Request`` document.
		property_name: Requested property.
		item_code: The property's service item.
		window: Optional ``(start, end)`` to use instead of the current lease
			window, used when the lease is being moved.

	Returns:
		Filters for ``frappe.get_all``, or ``None`` when the request has no
		customer or the lease no start, so it owns nothing.
	"""
	start, end = window or lease_window(service_request, property_name)
	if not (item_code and start and service_request.get("customer")):
		return None

	filters = [
		["item_code", "=", item_code],
		["customer", "=", service_request.customer],
		["valid_from", ">=", start],
	]
	if end:
		filters.append(["valid_from", "<=", end])

	return filters


def get_window_prices(
	service_request, property_name: str, item_code: str, price_list: str | None = None, window=None
) -> list[dict]:
	"""Return the Item Prices a request owns for one property, oldest first."""
	filters = window_filters(service_request, property_name, item_code, window)
	if filters is None:
		return []
	if price_list:
		filters.append(["price_list", "=", price_list])

	return frappe.get_all("Item Price", filters=filters, fields=PRICE_FIELDS, order_by="valid_from asc")


def property_service_items(service_request) -> dict[str, str]:
	"""Return ``{property: service item}`` for the request's active requested properties."""
	properties = [row.utility_property for row in active_rows(service_request)]
	if not properties:
		return {}

	return dict(
		frappe.get_all(
			"Utility Property",
			filters={"name": ("in", properties), "service_item": ("is", "set")},
			fields=["name", "service_item"],
			as_list=True,
		)
	)


def shared_service_items(service_request, items: set | None = None) -> dict[str, list[str]]:
	"""Return ``{service item: properties}`` for the request's items owned by several properties.

	Args:
		service_request: ``Utility Service Request`` document.
		items: Optional service items to limit the check to.
	"""
	own = set(property_service_items(service_request).values())
	if items is not None:
		own &= set(items)
	if not own:
		return {}

	owners: dict[str, list[str]] = {}
	for name, item_code in frappe.get_all(
		"Utility Property",
		filters={"service_item": ("in", list(own))},
		fields=["name", "service_item"],
		as_list=True,
	):
		owners.setdefault(item_code, []).append(name)

	return {item: sorted(names) for item, names in owners.items() if len(names) > 1}


def validate_unshared_service_items(service_request, items: set | None = None) -> None:
	"""Raise when a service item of the request belongs to more than one property.

	A shared item gives two properties the same prices, so a lease window no
	longer names one request and nothing may be written or deleted by it.
	"""
	shared = shared_service_items(service_request, items)
	if not shared:
		return

	frappe.throw(
		_(
			"The rent item of these properties is shared, so their Item Prices cannot be told apart "
			"by lease: {0}. Give each property its own service item first."
		).format(
			"; ".join(
				_("{0} is used by {1}").format(item, ", ".join(names)) for item, names in sorted(shared.items())
			)
		)
	)


def owns_price(service_request, price: dict) -> bool:
	"""Return whether an Item Price row belongs to the request by window and customer."""
	if not price or price.get("customer") != service_request.get("customer"):
		return False

	for property_name, item_code in property_service_items(service_request).items():
		if item_code != price.get("item_code"):
			continue
		start, end = lease_window(service_request, property_name)
		valid_from = getdate(price.get("valid_from")) if price.get("valid_from") else None
		if start and valid_from and valid_from >= start and (end is None or valid_from <= end):
			return True

	return False


def validate_within_window(service_request, property_name: str, periods) -> None:
	"""Block periods that start before or run past the property's lease.

	A price running past the lease end would start in this window but cover
	the next lease's dates, blocking its schedule and pricing its invoices.
	"""
	start, end = lease_window(service_request, property_name)
	for period in periods:
		valid_from = getdate(period.valid_from)
		valid_upto = getdate(period.valid_upto) if period.valid_upto else None
		if start and valid_from < start:
			frappe.throw(
				_("{0}: a rent period cannot start on {1}, before the lease starts on {2}.").format(
					property_name, valid_from, start
				)
			)
		if end and (valid_upto is None or valid_upto > end):
			frappe.throw(
				_("{0}: a rent period cannot run past the lease end {1}.").format(property_name, end)
			)


def delete_window_prices(service_request, price_list: str | None = None, items: set | None = None) -> int:
	"""Delete the Item Prices a request owns, optionally limited by price list or item.

	Never touches prices of another customer, blank customer prices, prices
	starting outside the window (another lease's), or items that are not the
	request's own service items.
	"""
	validate_unshared_service_items(service_request, items)

	names = []
	for property_name, item_code in property_service_items(service_request).items():
		if items is not None and item_code not in items:
			continue
		names += [row.name for row in get_window_prices(service_request, property_name, item_code, price_list)]

	for name in names:
		frappe.delete_doc("Item Price", name, ignore_permissions=True, force=True)

	return len(names)


def adjust_prices_to_window(service_request, before) -> None:
	"""Keep a request's prices inside its lease after the lease was moved.

	Prices are found with the old window. Those wholly outside the new window
	are deleted; those crossing a new boundary are cut to it. Dates the new
	window gains are left unpriced, so the schedule shows the gap.

	Args:
		service_request: Request as saved.
		before: The request before this update.
	"""
	if not is_item_price_approach():
		return

	for property_name, item_code in property_service_items(service_request).items():
		old = lease_window(before, property_name)
		new = lease_window(service_request, property_name)
		if old == new:
			continue

		start, end = new
		for price in get_window_prices(before, property_name, item_code, window=old):
			valid_from = getdate(price.valid_from)
			valid_upto = getdate(price.valid_upto) if price.valid_upto else None
			if (end and valid_from > end) or (valid_upto and valid_upto < start):
				frappe.delete_doc("Item Price", price.name, ignore_permissions=True, force=True)
				continue

			changes = {}
			if valid_from < start:
				changes["valid_from"] = start
			if end and (valid_upto is None or valid_upto > end):
				changes["valid_upto"] = end
			if changes:
				frappe.db.set_value("Item Price", price.name, changes, update_modified=False)


def validate_lease_move(service_request, before) -> None:
	"""Block moving a lease away from dates its submitted invoices already bill.

	Raises:
		frappe.ValidationError: When a submitted Sales Invoice of the request
			bills a property's service item on a date outside its new window,
			or a moved property's service item is shared, so its prices
			cannot follow the lease.
	"""
	if not is_item_price_approach():
		return

	moved = {
		item_code
		for property_name, item_code in property_service_items(service_request).items()
		if lease_window(before, property_name) != lease_window(service_request, property_name)
	}
	if moved:
		validate_unshared_service_items(service_request, moved)

	invoice = frappe.qb.DocType("Sales Invoice")
	line = frappe.qb.DocType("Sales Invoice Item")

	for property_name, item_code in property_service_items(service_request).items():
		start, end = lease_window(service_request, property_name)
		if lease_window(before, property_name) == (start, end):
			continue

		billed = (
			frappe.qb.from_(line)
			.join(invoice)
			.on(line.parent == invoice.name)
			.select(invoice.name, line.custom_posting_date, invoice.posting_date)
			.where(invoice.docstatus == 1)
			.where(invoice.utility_service_request == service_request.name)
			.where(line.item_code == item_code)
		).run(as_dict=True)

		for row in billed:
			date = getdate(row.custom_posting_date or row.posting_date)
			if (start and date < start) or (end and date > end):
				frappe.throw(
					_(
						"{0}: Sales Invoice {1} already bills {2}, outside the new lease {3} to {4}. "
						"Cancel or credit it first."
					).format(property_name, row.name, date, start, end or _("no end"))
				)
