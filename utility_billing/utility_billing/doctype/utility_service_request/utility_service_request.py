# Copyright (c) 2024, Navari and contributors
# For license information, please see license.txt

import frappe
import json
from erpnext.controllers.accounts_controller import AccountsController
from frappe import _
from frappe.contacts.address_and_contact import load_address_and_contact
from frappe.model.document import Document
from frappe.utils import add_months, nowdate, add_days


class UtilityServiceRequest(Document):
    def onload(self):
        load_address_and_contact(self)
        
    def validate(self):
        if self.service_request_from == "Customer":
            self.customer = self.party_name
        
    def on_submit(self):
        settings = frappe.get_doc("Utility Billing Settings", "Utility Billing Settings")
        if settings.create_customer_from_utility_service_request_on_submit:
            make_customer(self.name)
 

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


@frappe.whitelist()
def create_contract(name):
    """Create a contract from the Utility Service Request."""
    doc = frappe.get_doc("Utility Service Request", name)
    contract = frappe.new_doc("Contract")
    contract.party_type = "Customer"
    contract.party_name = doc.customer
    contract.utility_service_request = name
    contract.property = doc.utility_property
    contract.start_date = doc.start_date
    contract.end_date = doc.end_date
    contract.frequency = doc.frequency
    contract.flags.ignore_mandatory = True
    contract.insert()
    return contract.name


@frappe.whitelist()
def make_customer(name):
    """Create a customer from the Utility Service Request."""
    doc = frappe.get_doc("Utility Service Request", name)
    customer_doc = create_customer(doc)
    frappe.db.set_value("Utility Service Request", name, "customer", customer_doc.name)
    return customer_doc.name


def create_customer(doc):
    if doc.customer:
        return frappe.get_doc("Customer", doc.customer)
    
    from erpnext.selling.doctype.quotation.quotation import create_customer_from_lead, create_customer_from_prospect

    if doc.service_request_from == "Lead":
        existing_customer = frappe.db.get_value("Customer", {"lead_name": doc.party_name}, "name")
        if existing_customer:
            return frappe.get_doc("Customer", existing_customer)
        return create_customer_from_lead(doc.party_name, ignore_permissions=True)
    
    elif doc.service_request_from == "Prospect":
        existing_customer = frappe.db.get_value("Customer", {"prospect_name": doc.party_name}, "name")
        if existing_customer:
            return frappe.get_doc("Customer", existing_customer)
        return create_customer_from_prospect(doc.party_name, ignore_permissions=True)
    
    elif doc.service_request_from == "Customer":
        return frappe.get_doc("Customer", doc.party_name)


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
        "default_warehouse": (
            item.item_defaults[0].default_warehouse if item.item_defaults else None
        ),
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

    auto_submit_stock_entry = frappe.db.get_single_value(
        "Utility Billing Settings", "stock_entry_creation_state"
    )

    stock_entry = frappe.new_doc("Stock Entry")
    stock_entry.stock_entry_type = "Material Issue"

    for item in doc.items:
        if item.item_group == "Meter" and item.meter_number:
            stock_entry_item = item.as_dict()
            stock_entry_item.update(
                {
                    "serial_no": item.meter_number,
                    "use_serial_batch_fields": 1,
                    "s_warehouse": item.warehouse,
                }
            )
            stock_entry.append("items", stock_entry_item)

    if stock_entry.items:
        stock_entry.save()

        if auto_submit_stock_entry == "Submitted":
            stock_entry.submit()

    return {"stock_entry": stock_entry.name}


@frappe.whitelist()
def get_utility_bill_structure_details(name):
    structure = frappe.get_doc("Utility Bill Structure", name)

    items = []
    for row in structure.items:
        item = frappe.get_doc("Item", row.item)
        item_details = {
            "item_name": item.item_name,
            "item_code": item.item_code,
            "uom": item.stock_uom,
            "rate": row.amount,
            "amount": row.amount,
            "warehouse": (
                item.item_defaults[0].default_warehouse if item.item_defaults else None
            ),
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
            "default_warehouse": (
                item.item_defaults[0].default_warehouse if item.item_defaults else None
            ),
            "delivery_date": nowdate(),
        }
        items.append(item_details)

    dimension_fields = frappe.get_all("Accounting Dimension", filters={"disabled": 0}, fields=["fieldname"])
    dimensions = {}

    if hasattr(structure, 'cost_center'):
        dimensions['cost_center'] = structure.cost_center
    if hasattr(structure, 'project'):
        dimensions['project'] = structure.project

    for dim in dimension_fields:
        fieldname = dim.fieldname
        if hasattr(structure, fieldname):
            dimensions[fieldname] = getattr(structure, fieldname)

    return {
        "items": items,
        "dimensions": dimensions
    }



@frappe.whitelist()
def create_sales_order_doc(docname, items, customer=None, customer_name=None, transaction_date=None, company=None):
    """
    Create a Sales Order from Utility Service Request
    
    :param docname: Utility Service Request name
    :param items: List of item dictionaries containing:
        - item_code
        - qty
        - rate
        - amount
        - warehouse
        - item_name (optional)
    :param customer: Customer ID
    :param transaction_date: Order date
    :param company: Company 
    """
    if isinstance(items, str):
        try:
            items = json.loads(items)
        except Exception as e:
            frappe.throw(f"Failed to parse items JSON: {e}")

    if not isinstance(items, list):
        frappe.throw("Items must be a list of item dictionaries.")

    for item in items:
        if not item.get("item_code"):
            frappe.throw("Item Code is required for all items")
        if not item.get("qty"):
            frappe.throw("Quantity is required for all items")
        if item.get("rate") is None:  
            frappe.throw("Rate is required for all items")

    usr = frappe.get_doc("Utility Service Request", docname)

    so = frappe.new_doc("Sales Order")
    so.update({
        "customer": customer or usr.customer,
        "customer_name": customer_name,
        "payment_terms_template": usr.payment_terms_template,
        "tc_name": usr.tc_name,
        "terms": usr.terms,
        "company": company or usr.company or frappe.defaults.get_user_default("company"),
        "transaction_date": transaction_date or nowdate(),
        "delivery_date": add_days(transaction_date or nowdate(), 7),
        "utility_service_request": docname,
        "territory": usr.territory,
        "price_list": usr.price_list,
        "currency": usr.currency or frappe.defaults.get_user_default("currency"),
        "conversion_rate": 1.0,
        "selling_price_list": usr.price_list,
        "ignore_pricing_rule": 1,
    })
    
    for item in items:
        item_code = item.get("item_code")

        item_line = {
            "item_code": item_code,
            "item_name": item.get("item_name") or frappe.db.get_value("Item", item_code, "item_name"),
            "description": item.get("description") or frappe.db.get_value("Item", item_code, "description"),
            "uom": item.get("uom") or frappe.db.get_value("Item", item_code, "stock_uom"),
            "qty": float(item.get("qty", 0)),
            "rate": float(item.get("rate", 0)),
            "warehouse": item.get("warehouse") or frappe.defaults.get_user_default("warehouse"),
            "conversion_factor": 1.0,
        }

        item_line["amount"] = float(item.get("amount", item_line["qty"] * item_line["rate"]))

        for key, value in item.items():
            if key not in item_line:
                item_line[key] = value

        so.append("items", item_line)

    so.insert(ignore_permissions=True)
    
    if frappe.db.get_single_value("Utility Billing Settings", "sales_order_creation_state") == "Submitted":
        so.submit()

    frappe.get_doc({
        "doctype": "Comment",
        "comment_type": "Info",
        "reference_doctype": "Utility Service Request",
        "reference_name": docname,
        "content": f"Created Sales Order <a href='/app/sales-order/{so.name}'>{so.name}</a>"
    }).insert(ignore_permissions=True)

    return so.name


@frappe.whitelist()
def create_sales_invoice_doc(docname, items, customer=None, customer_name=None, posting_date=None, due_date=None, company=None, auto_repeat=None):
    """
    Create a Sales Invoice from Utility Service Request and optionally create an Auto Repeat.

    :param docname: Utility Service Request name
    :param items: List of item dictionaries containing:
        - item_code, qty, rate, amount, warehouse, item_name (optional)
    :param customer: Customer ID
    :param posting_date: Invoice date
    :param due_date: Due date
    :param company: Company
    :param auto_repeat: Dict or JSON string containing Auto Repeat settings or existing Auto Repeat name
    """
    # Load auto_repeat if it is a JSON string
    if isinstance(auto_repeat, str):
        try:
            auto_repeat = json.loads(auto_repeat)
        except Exception as e:
            auto_repeat = {}

    if isinstance(items, str):
        try:
            items = json.loads(items)
        except Exception as e:
            items = []

    if not isinstance(items, list):
        frappe.throw("Items must be a list of item dictionaries.")

    for item in items:
        if not item.get("item_code"):
            frappe.throw("Item Code is required for all items")
        if not item.get("qty"):
            frappe.throw("Quantity is required for all items")
        if item.get("rate") is None:
            frappe.throw("Rate is required for all items")

    usr = frappe.get_doc("Utility Service Request", docname)

    si = frappe.new_doc("Sales Invoice")
    si.update({
        "customer": customer or usr.customer,
        "customer_name": customer_name,
        "ignore_default_payment_terms_template": usr.ignore_default_payment_terms_template,
        "payment_terms_template": usr.payment_terms_template,
        "tc_name": usr.tc_name,
        "terms": usr.terms,
        "company": company or usr.company or frappe.defaults.get_user_default("company"),
        "posting_date": posting_date or nowdate(),
        "due_date": due_date or add_days(nowdate(), 30),
        "utility_service_request": docname,
        "currency": usr.currency or frappe.defaults.get_user_default("currency"),
        "price_list": usr.price_list,
        "selling_price_list": usr.price_list,
        "conversion_rate": 1.0,
        "ignore_pricing_rule": 1,
    })

    for item in items:
        item_code = item.get("item_code")

        item_line = {
            "item_code": item_code,
            "item_name": item.get("item_name") or frappe.db.get_value("Item", item_code, "item_name"),
            "description": item.get("description") or frappe.db.get_value("Item", item_code, "description"),
            "uom": item.get("uom") or frappe.db.get_value("Item", item_code, "stock_uom"),
            "qty": float(item.get("qty", 0)),
            "rate": float(item.get("rate", 0)),
            "warehouse": item.get("warehouse") or frappe.defaults.get_user_default("warehouse"),
            "conversion_factor": 1.0,
        }

        item_line["amount"] = float(item.get("amount", item_line["qty"] * item_line["rate"]))

        for key, value in item.items():
            if key not in item_line:
                item_line[key] = value

        si.append("items", item_line)

    si.insert(ignore_permissions=True)

    if frappe.db.get_single_value("Utility Billing Settings", "sales_invoice_creation_state") == "Submitted":
        si.submit()

    # Auto Repeat creation
    if isinstance(auto_repeat, dict) and auto_repeat.get("frequency") and auto_repeat.get("start_date"):
        repeat_doc = frappe.get_doc({
            "doctype": "Auto Repeat",
            "reference_doctype": "Sales Invoice",
            "reference_document": si.name,
            "frequency": auto_repeat.get("frequency"),
            "start_date": auto_repeat.get("start_date"),
            "end_date": auto_repeat.get("end_date"),
            "next_schedule_date": auto_repeat.get("start_date"),
            "submit_on_creation": auto_repeat.get("submit_on_creation", 1),
            "notify_by_email": 0,
            "repeat_on_day": auto_repeat.get("repeat_on_day"),
            "repeat_on_last_day": auto_repeat.get("repeat_on_last_day"),
            "auto_repeat_on_days": auto_repeat.get("repeat_on_days", []),
        })
        repeat_doc.insert(ignore_permissions=True)
        si.db_set("auto_repeat", repeat_doc.name)
        frappe.msgprint(
            f"Auto Repeat <a href='/app/auto-repeat/{repeat_doc.name}'>{repeat_doc.name}</a> created for this invoice."
        )

    frappe.get_doc({
        "doctype": "Comment",
        "comment_type": "Info",
        "reference_doctype": "Utility Service Request",
        "reference_name": docname,
        "content": f"Created Sales Invoice <a href='/app/sales-invoice/{si.name}'>{si.name}</a>"
    }).insert(ignore_permissions=True)

    return si.name
