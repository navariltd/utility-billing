import frappe
from frappe import _
from frappe.model.document import Document


def before_insert(doc: Document, method: str) -> None:
	"""A BOM made for a request never starts as the default.

	ERPNext still makes it the default on submit when the item has no submitted
	default yet, so the first BOM of an item keeps becoming the default. Ticking
	Is Default after the first save makes a later BOM the default on purpose.
	"""
	if doc.get("utility_service_request"):
		doc.is_default = 0


def validate(doc: Document, method: str) -> None:
	validate_request_item(doc)


def validate_request_item(doc: Document) -> None:
	"""A BOM linked to a request must be for one of the request's items.

	Runs from ``validate``, so on draft save and submit only.
	"""
	if not doc.get("utility_service_request"):
		return

	item_codes = frappe.get_all(
		"Utility Service Request Item",
		filters={"parent": doc.utility_service_request, "parenttype": "Utility Service Request"},
		pluck="item_code",
	)
	if doc.item not in item_codes:
		frappe.throw(
			_("{0} is not an item on {1}. Pick one of its items or remove the request.").format(
				doc.item, doc.utility_service_request
			)
		)
