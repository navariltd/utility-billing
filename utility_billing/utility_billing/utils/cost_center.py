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
	"""Return the cost center a primary request row of ``property_name`` defaults to.

	The property's own cost center, then the service item's Default Selling Cost
	Center for the company, then the company default. A cost center of another
	company is never used.
	"""
	candidates = (
		frappe.db.get_value("Utility Property", property_name, "cost_center"),
		frappe.db.get_value(
			"Item Default",
			{"parent": item_code, "parenttype": "Item", "company": company},
			"selling_cost_center",
		),
		frappe.get_cached_value("Company", company, "cost_center"),
	)
	for cost_center in candidates:
		if cost_center and frappe.get_cached_value("Cost Center", cost_center, "company") == company:
			return cost_center

	return None


def fill_request_item_cost_centers(doc) -> None:
	"""Default the cost center of each primary row of a Utility Service Request.

	A primary row bills a requested property's service item. It is matched by its
	own ``utility_property``, else by item when exactly one requested property owns
	that item; a service item shared by several is not guessed and stays blank.
	Rows with a cost center, secondary utility items, meter rows and other items
	are left to ERPNext's normal resolution.
	"""
	if not doc.get("company"):
		return

	requested = [row.utility_property for row in doc.get("requested_properties") or [] if row.utility_property]
	if not requested:
		return

	service_items = dict(
		frappe.get_all(
			"Utility Property",
			filters={"name": ["in", requested]},
			fields=["name", "service_item"],
			as_list=True,
		)
	)
	owners = {}
	for property_name, item_code in service_items.items():
		if item_code:
			owners.setdefault(item_code, []).append(property_name)

	for row in doc.get("items") or []:
		if row.get("cost_center") or not row.item_code:
			continue

		property_name = row.get("utility_property")
		if service_items.get(property_name) != row.item_code:
			candidates = owners.get(row.item_code) or []
			property_name = candidates[0] if len(candidates) == 1 else None

		if property_name:
			row.cost_center = resolve_primary_cost_center(property_name, row.item_code, doc.company)
