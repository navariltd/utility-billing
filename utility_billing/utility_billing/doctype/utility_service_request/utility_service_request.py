# Copyright (c) 2024, Navari and contributors
# For license information, please see license.txt

import frappe
from frappe.contacts.address_and_contact import load_address_and_contact
from frappe.model.document import Document


class UtilityServiceRequest(Document):
    def onload(self):
        load_address_and_contact(self)


@frappe.whitelist()
def create_customer_and_sales_order(docname):
    doc = frappe.get_doc("Utility Service Request", docname)
    customer_doc = create_customer(doc)
    sales_order_doc = create_sales_order(doc, customer_doc)
    return {"sales_order": sales_order_doc.name}


def create_customer(doc):
    """
    Create a new customer if not already linked to the Utility Service Request.
    """
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
        doc.customer = customer_doc.name
        doc.save()
    else:
        customer_doc = frappe.get_doc("Customer", doc.customer)

    return customer_doc


def create_sales_order(doc, customer_doc):
    """
    Create a new Sales Order linked to the provided customer.
    """
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

    doc.customer = customer_doc.name

    if auto_submit_sales_order != "Draft":
        sales_order_doc.submit()

    return sales_order_doc
