import frappe
from erpnext.stock.get_item_details import get_default_bom


def get_request_bom(request: str | None, item_code: str) -> str | None:
	"""Return the BOM a request uses for an item.

	That is the latest submitted, active BOM linked to the request, or the
	item's default BOM when the request has none of its own.
	"""
	if request:
		own = frappe.get_all(
			"BOM",
			filters={
				"utility_service_request": request,
				"item": item_code,
				"docstatus": 1,
				"is_active": 1,
			},
			order_by="creation desc",
			pluck="name",
			limit=1,
		)
		if own:
			return own[0]

	return get_default_bom(item_code)


def set_request_boms(doc, request: str | None) -> None:
	"""Point each item row of a draft at the BOM its request uses.

	Called from ``validate`` only, so it runs on save and submit of a draft and
	never on a submitted document.
	"""
	if doc.get("_action") == "update_after_submit":
		return

	boms = {}
	for row in doc.get("items") or []:
		if not row.item_code:
			continue
		if row.item_code not in boms:
			boms[row.item_code] = get_request_bom(request, row.item_code)
		row.bom_no = boms[row.item_code]
