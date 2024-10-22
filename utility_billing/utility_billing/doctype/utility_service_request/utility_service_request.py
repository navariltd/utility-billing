# Copyright (c) 2024, Navari and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.contacts.address_and_contact import load_address_and_contact
from frappe.model.document import Document


class UtilityServiceRequest(Document):
    def onload(self):
        load_address_and_contact(self)


@frappe.whitelist()
def create_customer_and_sales_order(docname):
    doc = frappe.get_doc("Utility Service Request", docname)
    customer_doc = create_customer(doc)
    link_contact_and_address_to_customer(customer_doc, doc)
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

        frappe.db.set_value(
            "Utility Service Request", doc.name, "customer", customer_doc.name
        )

        doc = frappe.get_doc("Utility Service Request", doc.name)
        doc.save()

    else:
        customer_doc = frappe.get_doc("Customer", doc.customer)

    return customer_doc


def link_contact_and_address_to_customer(customer_doc, doc):
    dynamic_links = frappe.db.get_all(
        "Dynamic Link",
        filters={
            "link_doctype": "Utility Service Request",
            "link_name": doc.name,
            "parenttype": ["in", ["Contact", "Address"]],
        },
        fields=["parent", "parenttype"],
    )
    for link in dynamic_links:
        new_link = frappe.get_doc(
            {
                "doctype": "Dynamic Link",
                "parent": link.parent,
                "parenttype": link.parenttype,
                "link_doctype": "Customer",
                "link_name": customer_doc.name,
            }
        )
        new_link.insert(ignore_permissions=True)

    frappe.db.commit()


def create_sales_order(doc, customer_doc):
    auto_submit_sales_order = frappe.db.get_single_value(
        "Utility Billing Settings", "sales_order_creation_state"
    )

    sales_order_doc = frappe.new_doc("Sales Order")
    sales_order_doc.customer = customer_doc.name
    sales_order_doc.utility_service_request = doc.name
    sales_order_doc.transaction_date = frappe.utils.nowdate()
    sales_order_doc.delivery_date = frappe.utils.nowdate()

    for item in doc.items:
        sales_order_doc.append(
            "items",
            {"item_code": item.item_code, "qty": item.qty or 1, "rate": item.rate or 0},
        )

    sales_order_doc.insert()

    if auto_submit_sales_order != "Draft":
        sales_order_doc.submit()

    return sales_order_doc


@frappe.whitelist()
def create_site_survey(docname):
    """Create a site survey as an issue for the utility service request."""
    doc = frappe.get_doc("Utility Service Request", docname)
    request_type_description = frappe.db.get_value(
        "Issue Type", doc.request_type, "description"
    )

    issue_doc = frappe.new_doc("Issue")
    issue_doc.subject = f"Site Survey for {docname} ({doc.customer_name})"
    issue_doc.description = (
        f"Site survey created for Utility Service Request: {docname}, Customer name: {doc.customer_name}.\n"
        f"{request_type_description}"
    )
    issue_doc.utility_service_request = docname
    issue_doc.issue_type = doc.request_type

    issue_doc.insert()
    doc.save()

    return {"issue": issue_doc.name}


@frappe.whitelist()
def create_bom(docname, item_code):
    bom = frappe.new_doc("BOM")
    bom.item = item_code
    bom.utility_service_request = docname
    bom.items = []
    bom.flags.ignore_mandatory = True
    bom.flags.ignore_validate = True
    bom.save()

    return {"bom": bom.name}


@frappe.whitelist()
def check_request_status(request_name):
    issues = frappe.get_list(
        "Issue", filters={"utility_service_request": request_name}, pluck="status"
    )

    submitted_boms = frappe.get_list(
        "BOM", filters={"utility_service_request": request_name}, pluck="docstatus"
    )

    status = frappe.get_doc("Utility Service Request", request_name).request_status

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


@frappe.whitelist()
def get_item_details(item_code, price_list=None):
    item = frappe.get_doc("Item", item_code)

    if not item:
        frappe.throw(_("Item not found"))

    default_warehouse = getattr(item, "default_warehouse", None)

    item_details = {
        "item_name": item.item_name,
        "uom": item.stock_uom,
        "rate": item.standard_rate,
        "warehouse": default_warehouse,
        "description": item.description,
        "qty": 1,
        "conversion_factor": (
            (item.uoms[0] or {}).get("conversion_factor", 1) if item.uoms else 1
        ),
        "brand": item.brand,
        "item_group": item.item_group,
        "stock_uom": item.stock_uom,
        "bom_no": item.default_bom,
        "weight_per_unit": item.weight_per_unit,
        "weight_uom": item.weight_uom,
    }

    if price_list:
        item_price = frappe.db.get_value(
            "Item Price",
            filters={"price_list": price_list, "item_code": item_code},
            fieldname=["price_list_rate"],
        )
        if item_price:
            item_details["rate"] = item_price

    return item_details
