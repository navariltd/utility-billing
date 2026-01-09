import frappe


def _delete_linked_documents(doctype_to_delete: str, link_field: str, asset_name: str) -> None:
	"""
	Helper function to cancel and delete documents linked to a specific asset.
	It iterates through documents of a given doctype that link to the specified asset,
	cancels them if submitted (docstatus == 1), and then deletes them.
	"""
	docs_to_delete = frappe.get_all(
		doctype_to_delete, filters={link_field: asset_name}, fields=["name", "docstatus"]
	)

	if not docs_to_delete:
		return

	for doc_data in docs_to_delete:
		try:
			doc = frappe.get_doc(doctype_to_delete, doc_data.name)
			if hasattr(doc, "docstatus") and doc.docstatus == 1:
				doc.cancel()
			frappe.delete_doc(doctype_to_delete, doc_data.name, ignore_permissions=True)
		except Exception as e:
			frappe.db.rollback()
			frappe.log_error(
				f"Error deleting {doctype_to_delete} {doc_data.name} linked to Asset {asset_name}: {e}"
			)


def _delete_item_if_solely_linked_to_asset(item_code: str, asset_name: str, demo_company: str) -> None:
	"""
	Deletes an Item if it's primarily associated with the given demo asset
	and not actively linked to other assets within the same demo company.
	"""
	if not item_code:
		return

	other_assets_with_this_item = frappe.get_all(
		"Asset",
		filters={
			"item_code": item_code,
			"company": demo_company,
			"name": ["!=", asset_name],
			"docstatus": ["<", 2],
		},
		limit=1,
	)

	if not other_assets_with_this_item:
		try:
			if frappe.db.exists("Item", item_code):
				frappe.delete_doc("Item", item_code, ignore_permissions=True)
			else:
				frappe.logger().debug(
					f"Item {item_code} not found, skipping deletion for Asset: {asset_name}"
				)
		except Exception as e:
			frappe.db.rollback()
			frappe.log_error(f"Error deleting Item {item_code} associated with Asset {asset_name}: {e}")
	else:
		frappe.logger().debug(f"Item {item_code} is linked to other assets in {demo_company}, not deleting.")


def delete_assets() -> None:
	"""
	Main function to clear all Asset records for a specified demo company
	and all their connected child and related documents.
	This function should only be accessible by System Managers.

	Args:
	    demo_company (str): The name of the demo company whose assets are to be cleared.
	"""
	demo_company = "Utility and Rental (Demo)"
	demo_assets = frappe.get_all(
		"Asset", filters={"company": demo_company}, fields=["name", "docstatus", "item_code"]
	)

	if not demo_assets:
		return

	for asset_data in demo_assets:
		asset_name = asset_data.name
		item_code = asset_data.item_code

		try:
			linked_doctypes = [
				("Asset Maintenance", "asset_name"),
				("Asset Repair", "asset"),
				("Asset Value Adjustment", "asset"),
				("Asset Depreciation Schedule", "asset"),
				("Asset Activity", "asset"),
			]

			for doctype, link_field in linked_doctypes:
				_delete_linked_documents(doctype, link_field, asset_name)

			asset_doc = frappe.get_doc("Asset", asset_name)
			if asset_doc.docstatus == 1:
				asset_doc.cancel()

			frappe.delete_doc("Asset", asset_name, ignore_permissions=True)

			_delete_item_if_solely_linked_to_asset(item_code, asset_name, demo_company)

		except Exception as e:
			frappe.db.rollback()
			frappe.log_error(f"Failed to delete Asset {asset_name} and its linked documents: {e}")
			frappe.logger().error(f"Skipping Asset {asset_name} due to error.")
