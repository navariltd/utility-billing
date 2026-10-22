"""Property details for the portal, including the caller's own billing documents.

Access rules enforced by :func:`get_property_details`:

* the tenant of the unit (current or past allocation) always gets the full
  payload, including the documents returned by
  :mod:`utility_billing.api.portal.property_documents`;
* anybody else (including guests) only gets the details of a property that is
  publicly available for rent, so occupied or reserved units are never disclosed
  to third parties.
"""

import frappe
from frappe import _
from frappe.utils import cint

from utility_billing.api.portal.property_documents import get_property_documents
from utility_billing.api.portal.properties import (
	HISTORY,
	PROPERTY_FIELDS,
	get_tenant_properties,
)
from utility_billing.api.portal.roles import (
	GUEST,
	get_linked_customers,
	is_guest,
)

DETAILS_EXTRA_FIELDS = ("is_group", "lot_size", "unique_features", "legal_description")


@frappe.whitelist(allow_guest=True)
def get_property_details(property: str) -> dict:
	"""Return the details of a single property, plus the caller's own documents.

	Args:
	    property: ``Utility Property`` name.

	Returns:
	    Dict with ``property``, ``tenancy``, ``is_mine``, ``is_available``,
	    ``can_book`` and ``documents`` (``None`` unless the property is the
	    caller's).

	Raises:
	    frappe.ValidationError: When no property was provided.
	    frappe.DoesNotExistError: When the property does not exist.
	    frappe.PermissionError: When the property is not available and not the caller's.
	"""
	property_name = (property or "").strip()
	if not property_name:
		frappe.throw(_("No property was provided."))

	property_doc = _get_property_doc(property_name)
	if not property_doc:
		frappe.throw(
			_("Property {0} was not found.").format(property_name),
			frappe.DoesNotExistError,
		)

	customers = [] if is_guest() else get_linked_customers()
	tenancy = _find_tenancy(property_name, frappe.session.user)
	is_available = property_doc.get("status") == "Available" and not cint(
		property_doc.get("is_group")
	)

	if not tenancy and not is_available:
		frappe.throw(_("This property is not available."), frappe.PermissionError)

	documents = (
		get_property_documents(
			property_name, [customer["name"] for customer in customers]
		)
		if tenancy
		else None
	)

	return {
		"property": property_doc,
		"tenancy": tenancy,
		"is_mine": bool(tenancy),
		"is_available": is_available,
		"can_book": is_available and not tenancy,
		"documents": documents,
	}


def _get_property_doc(property_name: str) -> dict | None:
	"""Return the descriptive fields of a property with its features and gallery."""
	property_doc = frappe.db.get_value(
		"Utility Property",
		property_name,
		[*PROPERTY_FIELDS, *DETAILS_EXTRA_FIELDS],
		as_dict=True,
	)

	if not property_doc:
		return None

	details = dict(property_doc)
	details["features"] = frappe.db.get_all(
		"Utility Property Feature item",
		filters={"parent": property_name},
		fields=["feature", "feature_type", "notes"],
	)
	details["image_gallery"] = frappe.db.get_all(
		"Property Gallery Image",
		filters={"parent": property_name},
		fields=["image", "title", "description"],
	)

	return details


def _find_tenancy(property_name: str, user: str) -> dict | None:
	"""Return the caller's allocation for the property (current or history), if any."""
	if not user or user == GUEST:
		return None

	properties = get_tenant_properties(user)
	for row in [*properties["current"], *properties["history"]]:
		if row["utility_property"] == property_name:
			return {**row, "is_current": row["state"] != HISTORY}

	return None
