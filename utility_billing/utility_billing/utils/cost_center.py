"""Cost Center of a Utility Property.

Every billable property may own a Cost Center for tracking its rent and
expenses. When auto creation is enabled in Utility Billing Settings, a
missing one is created on demand, nested under the default parent Cost
Center configured for the property's company. Once resolved, it is synced
onto the property's own service item as an Item Default, so Sales Invoice
lines billing that item pick it up automatically.
"""

import frappe
from frappe import _


def ensure_property_cost_center(property_doc) -> str | None:
	"""Return the Cost Center of a property, creating it when missing.

	Args:
		property_doc: ``Utility Property`` document.

	Returns:
		The Cost Center name, or ``None`` when auto creation is disabled and
		the property has no Cost Center yet.
	"""
	if property_doc.cost_center and frappe.db.exists("Cost Center", property_doc.cost_center):
		return property_doc.cost_center

	return create_cost_center_for_property(property_doc)


def create_cost_center_for_property(property_doc) -> str | None:
	"""Create (or link) the Cost Center of a property.

	The Cost Center is a leaf named after the property, nested under the
	default parent Cost Center configured for the property's company. When a
	Cost Center of that name already exists it is linked instead of being
	created, so repeated calls stay idempotent.

	Args:
		property_doc: ``Utility Property`` document.

	Returns:
		The Cost Center name, or ``None`` when auto creation is disabled, the
		property has no name to derive it from, or no default parent is
		configured for its company.
	"""
	settings = get_settings()
	if not settings.auto_create_property_cost_center:
		return None

	if not property_doc.property_name:
		return None

	parent_cost_center = _default_parent_cost_center(settings, property_doc.company)
	if not parent_cost_center:
		return None

	company = frappe.db.get_value("Cost Center", parent_cost_center, "company")
	abbr = frappe.db.get_value("Company", company, "abbr")
	cost_center_name = f"{property_doc.property_name} - {abbr}"

	if frappe.db.exists("Cost Center", cost_center_name):
		return cost_center_name

	cost_center_doc = frappe.get_doc(
		{
			"doctype": "Cost Center",
			"cost_center_name": property_doc.property_name,
			"company": company,
			"parent_cost_center": parent_cost_center,
			"is_group": 0,
		}
	)
	cost_center_doc.flags.ignore_mandatory = True
	cost_center_doc.insert(ignore_permissions=True)

	return cost_center_doc.name


def sync_cost_center_to_service_item(property_doc) -> None:
	"""Set the property's Cost Center as an Item Default of its service item.

	Only fills a company's row when it has no Cost Center yet - an existing
	value is left alone, since it may have been set deliberately. Only ever
	touches the property's own service item, never a secondary utility item,
	since those are not owned by a single property.

	The Item's document cache is cleared after saving, since ERPNext's own
	item-detail resolution (``get_item_defaults``) reads a cached copy of the
	Item and would otherwise keep returning the value from before this sync,
	even though the database itself is already correct.

	Args:
		property_doc: ``Utility Property`` document.
	"""
	if not property_doc.service_item or not property_doc.cost_center or not property_doc.company:
		return

	item_doc = frappe.get_doc("Item", property_doc.service_item)

	row = next(
		(r for r in item_doc.get("item_defaults") or [] if r.company == property_doc.company),
		None,
	)

	if row:
		if row.selling_cost_center:
			return
		row.selling_cost_center = property_doc.cost_center
	else:
		item_doc.append(
			"item_defaults",
			{
				"company": property_doc.company,
				"selling_cost_center": property_doc.cost_center,
			},
		)

	item_doc.save(ignore_permissions=True)
	frappe.clear_document_cache("Item", item_doc.name)

def _default_parent_cost_center(settings, company: str | None) -> str | None:
	"""Return the default Parent Cost Center configured for a company.

	Args:
		settings: ``Utility Billing Settings`` document.
		company: Company the property belongs to.

	Returns:
		The configured parent, or ``None`` when the property has no company
		or no row matches it.
	"""
	if not company:
		return None

	for row in settings.get("default_parent_cost_centers") or []:
		if row.company == company and row.parent_cost_center:
			return row.parent_cost_center

	return None


def get_settings():
	"""Return the cached Utility Billing Settings document."""
	return frappe.get_cached_doc("Utility Billing Settings")


def resolve_primary_cost_center(property_name: str, item_code: str, company: str) -> str | None:
	"""Return the cost center a request row or invoice line of ``property_name`` takes.

	The property's own cost center wins; without one, ERPNext's fallback for the
	item (see ``default_cost_center``) applies. A cost center of another company
	is never used.
	"""
	candidates = (
		frappe.db.get_value("Utility Property", property_name, "cost_center"),
		default_cost_center(item_code, company),
	)
	for cost_center in candidates:
		if cost_center and frappe.get_cached_value("Cost Center", cost_center, "company") == company:
			return cost_center

	return None


def default_cost_center(item_code: str, company: str) -> str | None:
	"""Return the cost center ERPNext gives a selling line of ``item_code``.

	The item's Default Selling Cost Center, then its Item Group's, then its
	Brand's, then the company default, as ERPNext fills a new line.
	"""
	from erpnext.stock.get_item_details import get_default_cost_center

	ctx = frappe._dict(item_code=item_code, company=company, customer=True)

	return get_default_cost_center(ctx, company=company) or frappe.get_cached_value(
		"Company", company, "cost_center"
	)


def service_item_owners(properties: list[str]) -> dict[str, list[str]]:
	"""Return ``{service item: properties}`` for the given properties."""
	owners: dict[str, list[str]] = {}
	for property_name, item_code in frappe.get_all(
		"Utility Property",
		filters={"name": ("in", properties), "service_item": ("is", "set")},
		fields=["name", "service_item"],
		as_list=True,
	):
		owners.setdefault(item_code, []).append(property_name)

	return owners


def request_row_property(row, requested: list[str], owners: dict[str, list[str]]) -> str | None:
	"""Return the requested property a request row or invoice line belongs to.

	Its own ``utility_property`` when that property is requested; else the only
	requested property; else the one requested property whose service item it
	bills. Anything else is not guessed and gives ``None``.
	"""
	if row.get("utility_property") in requested:
		return row.utility_property

	if len(requested) == 1:
		return requested[0]

	candidates = owners.get(row.get("item_code")) or []

	return candidates[0] if len(candidates) == 1 else None


def requested_properties(service_request) -> list[str]:
	"""Return the properties a request still holds, in row order, without repeats."""
	from utility_billing.utility_billing.utils.request_prices import active_rows

	return list(dict.fromkeys(row.utility_property for row in active_rows(service_request)))


def fill_request_item_cost_centers(doc, skip_rows: set[str] | None = None) -> None:
	"""Default the cost center of each row of a Utility Service Request from its property.

	Only under the Item Price approach. With requested properties every row,
	rent item or not, takes the cost center of its property (see
	``request_row_property``), so the property wins over the item's own
	default. A row that already has a cost center, set by hand or earlier, is
	left alone, as are meter rows, rows whose property cannot be told and
	``skip_rows`` (rows already submitted, whose cost center is fixed).
	Without a requested property nothing is filled, so invoice lines follow
	ERPNext's fallback.
	"""
	from utility_billing.utility_billing.utils.request_prices import is_item_price_approach

	if not doc.get("company") or not is_item_price_approach():
		return

	requested = requested_properties(doc)
	if not requested:
		return

	owners = service_item_owners(requested)

	for row in doc.get("items") or []:
		if (
			row.get("cost_center")
			or not row.item_code
			or row.get("meter_number")
			or row.name in (skip_rows or set())
		):
			continue

		property_name = request_row_property(row, requested, owners)
		if property_name:
			row.cost_center = resolve_primary_cost_center(property_name, row.item_code, doc.company)
