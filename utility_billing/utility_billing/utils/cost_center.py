"""Cost Center of a Utility Property.

Every billable property may own a Cost Center for tracking its rent and
expenses. When auto creation is enabled in Utility Billing Settings, a
missing one is created on demand, nested under the property's own Parent
Cost Center if it has one, otherwise under the default parent configured
for the property's company.
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
	property's own Parent Cost Center if it has one, otherwise under the
	default parent configured for the property's company. When a Cost Center
	of that name already exists it is linked instead of being created, so
	repeated calls stay idempotent.

	Args:
		property_doc: ``Utility Property`` document.

	Returns:
		The Cost Center name, or ``None`` when auto creation is disabled, the
		property has no name to derive it from, or no parent could be
		resolved for its company.

	Raises:
		frappe.ValidationError: When the resolved parent belongs to a company
			other than the property's own.
	"""
	settings = get_settings()
	if not settings.auto_create_property_cost_center:
		return None

	if not property_doc.property_name:
		return None

	parent_cost_center = property_doc.parent_cost_center or _default_parent_cost_center(
		settings, property_doc.company
	)
	if not parent_cost_center:
		return None

	company = frappe.db.get_value("Cost Center", parent_cost_center, "company")

	if property_doc.company and company != property_doc.company:
		frappe.throw(
			_("Parent Cost Center {0} belongs to {1}, not {2}, the property's own company.").format(
				frappe.bold(parent_cost_center), company, property_doc.company
			)
		)

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