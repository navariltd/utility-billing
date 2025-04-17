import frappe

def create_utility_property_dimension():
    dimension_name = "Utility Property"
    ref_doctype = "Utility Property"

    if not frappe.db.exists("Accounting Dimension", {"document_type": ref_doctype}):
        dimension = frappe.get_doc({
            "doctype": "Accounting Dimension",
            "document_type": ref_doctype,
            "label": dimension_name,
            "disabled": 0,
            "dimension_defaults": [
                {
                    "company": company.name,
                    "mandatory_for_pl": 1,
                    "mandatory_for_bs": 1
                }
                for company in frappe.get_all("Company", fields=["name"])
            ]
        })
        dimension.insert(ignore_permissions=True)
        frappe.db.commit()
