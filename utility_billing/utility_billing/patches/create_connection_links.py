import frappe

def execute():
    target_links = [
        {"link_doctype": "Meter Reading", "link_fieldname": "customer", "group": "Utility Billing"},
        {"link_doctype": "Utility Service Request", "link_fieldname": "customer", "group": "Utility Billing"}, 
        {"link_doctype": "Contract", "link_fieldname": "party_name", "group": "Utility Billing"}, 
    ]

    customer_doc = frappe.get_doc("DocType", "Customer")

    # Ensure 'links' list exists
    existing_links = getattr(customer_doc, "links", [])

    for link in target_links:
        if not any(
            l.link_doctype == link["link_doctype"] and l.link_fieldname == link["link_fieldname"]
            for l in existing_links
        ):
            customer_doc.append("links", link)

    if customer_doc.get("links"):
        customer_doc.save()
        frappe.db.commit()
