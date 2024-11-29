# Copyright (c) 2024, Navari and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.contacts.address_and_contact import load_address_and_contact
from frappe.model.document import Document
from frappe.utils import nowdate, add_months
from erpnext.controllers.accounts_controller import AccountsController


class UtilityServiceRequest(Document):
    def onload(self):
        load_address_and_contact(self)
 

@frappe.whitelist()
def create_customer_and_sales_order(docname):
    doc = frappe.get_doc("Utility Service Request", docname)
    customer_doc = create_customer(doc)
    link_contact_and_address_to_customer(customer_doc, doc)
    sales_order_doc = create_sales_order(doc, customer_doc)
    create_stock_entry_for_meter_issue(docname)
    for item in doc.items:
        if item.item_group == "Meter" and item.meter_number:
            create_warranty_claim(customer_doc, item.meter_number, item.item_code)

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
        customer_doc.utility_property = doc.property

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
    sales_order_doc.utility_property = doc.property
    sales_order_doc.transaction_date = frappe.utils.nowdate()
    sales_order_doc.delivery_date = add_months(sales_order_doc.transaction_date, 1)

    for item in doc.items:
        item_dict = item.as_dict()
        item_dict["delivery_date"] = sales_order_doc.delivery_date
        sales_order_doc.append("items", item_dict)

    sales_order_doc.insert()
    
    AccountsController.append_taxes_from_item_tax_template(sales_order_doc)
    sales_order_doc.save()

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
        f"{' ' + request_type_description if request_type_description else ''}",
    )
    issue_doc.utility_service_request = docname
    issue_doc.issue_type = doc.request_type

    issue_doc.insert()

    return {"issue": issue_doc.name}


@frappe.whitelist()
def create_bom(docname, item_code):
    bom = frappe.new_doc("BOM")
    bom.item = item_code
    bom.utility_service_request = docname
    bom.raw_material_cost = 1   
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
        "item_code": item.item_code,
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
        "item_tax_template": item.taxes[0].item_tax_template if item.taxes else None,
        "default_warehouse": item.item_defaults[0].default_warehouse if item.item_defaults else None,
        "delivery_date": nowdate(),
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


@frappe.whitelist()
def bom_new_version(bom):
    bom = frappe.get_doc("BOM", bom)
    return frappe.copy_doc(bom)


def create_warranty_claim(customer_doc, serial_number, item_code):
    warranty_claim = frappe.new_doc("Warranty Claim")
    warranty_claim.customer = customer_doc.name 
    warranty_claim.complaint = customer_doc.name     
    warranty_claim.serial_no = serial_number
    warranty_claim.item_code = item_code
    warranty_claim.complaint_date = nowdate()
    warranty_claim.status = "Closed"
    warranty_claim.save()
    return warranty_claim


@frappe.whitelist()
def create_stock_entry_for_meter_issue(docname):
    doc = frappe.get_doc("Utility Service Request", docname)

    auto_submit_stock_entry = frappe.db.get_single_value("Utility Billing Settings", "stock_entry_creation_state")

    stock_entry = frappe.new_doc("Stock Entry")
    stock_entry.stock_entry_type = "Material Issue"

    for item in doc.items:
        if item.item_group == "Meter" and item.meter_number:
            stock_entry_item = item.as_dict()
            stock_entry_item.update({
                "serial_no": item.meter_number, 
                "use_serial_batch_fields": 1,                  
                "s_warehouse": item.warehouse,  
            })
            stock_entry.append("items", stock_entry_item)
            
    if stock_entry.items:
        stock_entry.save()

        if auto_submit_stock_entry == "Submitted":
            stock_entry.submit()

    return {"stock_entry": stock_entry.name}
