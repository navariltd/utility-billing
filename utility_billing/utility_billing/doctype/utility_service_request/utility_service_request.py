# Copyright (c) 2024, Navari and contributors
# For license information, please see license.txt

import json

import frappe
from frappe.contacts.address_and_contact import load_address_and_contact
from frappe.model.document import Document


class UtilityServiceRequest(Document):
    def onload(self):
        load_address_and_contact(self)


@frappe.whitelist()
def create_customer_and_sales_order(docname):
    doc = frappe.get_doc("Utility Service Request", docname)

    # Create or retrieve customer
    customer_doc = create_customer(doc)

    # Re-fetch the Utility Service Request document to get the latest version
    doc = frappe.get_doc("Utility Service Request", docname)

    # Create sales order after fetching the latest document
    sales_order_doc = create_sales_order(doc, customer_doc)

    return {"sales_order": sales_order_doc.name}


def create_customer(doc):
    if not doc.customer:
        customer_doc = frappe.new_doc("Customer")
        customer_doc.customer_name = doc.customer_name
        customer_doc.customer_type = doc.customer_type
        customer_doc.customer_group = doc.customer_group
        customer_doc.territory = doc.territory
        customer_doc.tax_id = doc.tax_id
        customer_doc.nrc_or_passport_no = doc.nrcpassport_no
        customer_doc.company = doc.company
        customer_doc.insert()

        # Set the customer on the Utility Service Request document
        frappe.db.set_value(
            "Utility Service Request", doc.name, "customer", customer_doc.name
        )

        # Re-fetch the Utility Service Request document to avoid the "modified" error
        doc = frappe.get_doc("Utility Service Request", doc.name)
        doc.save()

    else:
        customer_doc = frappe.get_doc("Customer", doc.customer)

    return customer_doc


def create_sales_order(doc, customer_doc):
    auto_submit_sales_order = frappe.db.get_single_value(
        "Utility Billing Settings", "sales_order_creation_state"
    )

    sales_order_doc = frappe.new_doc("Sales Order")
    sales_order_doc.customer = customer_doc.name
    sales_order_doc.transaction_date = frappe.utils.nowdate()

    for item in doc.items:
        sales_order_doc.append(
            "items",
            {"item_code": item.item_code, "qty": item.qty or 1, "rate": item.rate or 0},
        )

    sales_order_doc.insert()

    # Set the sales order on the Utility Service Request document
    frappe.db.set_value(
        "Utility Service Request", doc.name, "sales_order", sales_order_doc.name
    )

    if auto_submit_sales_order != "Draft":
        sales_order_doc.submit()

    return sales_order_doc


@frappe.whitelist()
def create_site_survey(docname):
    """Create a site survey as an issue for the utility service request."""
    doc = frappe.get_doc("Utility Service Request", docname)

    issue_doc = frappe.new_doc("Issue")
    issue_doc.subject = f"Site Survey for {docname}"
    issue_doc.description = (
        f"Site survey created for Utility Service Request: {docname}."
    )
    issue_doc.utility_service_request = docname

    issue_doc.insert()
    doc.save()

    return {"issue": issue_doc.name}


@frappe.whitelist()
def create_bom(docname, item_code, items):
    try:
        items = json.loads(items)
    except json.JSONDecodeError as e:
        frappe.throw(f"Error parsing items: {e}")

    bom = frappe.new_doc("BOM")
    bom.item = item_code
    bom.utility_service_request = docname

    for item in items:
        bom.append(
            "items",
            {
                "item_code": item["item_code"],
                "qty": item["qty"],
            },
        )

    bom.save()

    return bom.name


@frappe.whitelist()
def check_request_status(request_name):
    issues = frappe.get_list(
        "Issue", filters={"utility_service_request": request_name}, pluck="status"
    )

    submitted_boms = frappe.get_list(
        "BOM", filters={"utility_service_request": request_name}, pluck="docstatus"
    )

    status = frappe.get_doc("Utility Service Request", request_name).status

    if submitted_boms:
        if any(int(bom) == 1 for bom in submitted_boms):
            status = "BOM Completed"
        else:
            status = "BOM Created"

    elif issues:
        if any(issue in ["Resolved", "Closed"] for issue in issues):
            status = "Site Survey Completed"
        else:
            status = "Site Survey Created"
    else:
        status = ""

    return status
