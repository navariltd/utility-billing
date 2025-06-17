# Copyright (c) 2024, Navari and contributors
# For license information, please see license.txt

import frappe
import json
from erpnext.controllers.accounts_controller import AccountsController
from frappe import _
from frappe.contacts.address_and_contact import load_address_and_contact
from frappe.model.document import Document
from frappe.utils import add_months, nowdate, add_days, getdate


class UtilityServiceRequest(Document):
    def onload(self):
        load_address_and_contact(self)

    def validate(self):
        self.validate_items()
        self.set_customer_if_needed()
        self.validate_contract_dates()
        self.validate_child_items()

    def before_update_after_submit(self):
        # Re-run validation logic when updating after submission
        self.validate_contract_dates()
        self.validate_child_items()

    def set_customer_if_needed(self):
        if self.service_request_from == "Customer":
            self.customer = self.party_name
        
    def before_submit(self):
        self.status = "To Bill"
        
    def on_submit(self):
        settings = frappe.get_doc("Utility Billing Settings", "Utility Billing Settings")
        if settings.create_customer_from_utility_service_request_on_submit:
            make_customer(self.name)
            
    def validate_items(self):
        if not self.items:
            if not self.utility_bill_structure:
                frappe.throw(_("At least one item is required in the Utility Service Request."))
            else:
                response = get_utility_bill_structure_details(self.utility_bill_structure)
                
                self.items = []
                for item in response.get('items', []):
                    item_row = self.append('items', {})
                    for field, value in item.items():
                        item_row.set(field, value)
                
                dimensions = response.get('dimensions', {})
                for field, value in dimensions.items():
                    if hasattr(self, field):
                        self.set(field, value)
                        
    def validate_contract_dates(self):
        if self.start_date and self.end_date and getdate(self.start_date) > getdate(self.end_date):
            frappe.throw("Contract start date cannot be after the end date.")
            
        if self.start_date and self.contract_length_months and not self.end_date:
            self.end_date = add_months(getdate(self.start_date), self.contract_length_months)
            
        elif self.end_date and self.contract_length_months and not self.start_date:
            self.start_date = add_months(getdate(self.end_date), -self.contract_length_months)
            
        elif self.start_date and self.end_date:
            self.contract_length_months = self.get_month_diff(getdate(self.start_date), getdate(self.end_date))
            
        if self.start_date and self.contract_length_months and self.end_date:
            expected_end = add_months(getdate(self.start_date), self.contract_length_months)
            if getdate(expected_end) != getdate(self.end_date):
                self.end_date = expected_end

    def validate_child_items(self):
        parent_start = getdate(self.start_date) if self.start_date else None
        parent_end = getdate(self.end_date) if self.end_date else None

        for row in self.requested_properties:
            row_start = getdate(row.start_date) if row.start_date else None
            row_end = getdate(row.end_date) if row.end_date else None
            length = row.contract_length_months

            if row_start and parent_start and row_start < parent_start:
                frappe.throw(f"Property start date '{row_start}' in row {row.idx} cannot be before contract start date '{parent_start}'.")

            if row_end and parent_end and row_end > parent_end:
                frappe.throw(f"Property end date '{row_end}' in row {row.idx} cannot be after contract end date '{parent_end}'.")

            if row_start and row_end:
                row.contract_length_months = self.get_month_diff(row_start, row_end)

            elif row_start and length is not None:
                new_end = add_months(row_start, length)
                if parent_end and new_end > parent_end:
                    row.end_date = parent_end
                else:
                    row.end_date = new_end

    def get_month_diff(self, start, end):
        """Return month difference between two date objects"""
        if not start or not end:
            return 0

        months = (end.year - start.year) * 12 + (end.month - start.month)
        if end.day < start.day:
            months -= 1

        return max(months, 0)

        
  
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
    contract.start_date = doc.start_date
    contract.end_date = doc.end_date
    contract.contract_template = doc.contract_template
    contract.contract_terms = doc.contract_terms
    contract.requires_fulfilment = doc.requires_fulfilment
    contract.fulfilment_terms = doc.fulfilment_terms

    # Fields to ignore
    ignore_fields = {"parent", "parenttype", "parentfield", "idx", "name", 
                     "creation", "modified", "owner", "docstatus"}

    for item in doc.requested_properties:
        row_data = {}
        for key, value in item.as_dict().items():
            if key not in ignore_fields:
                row_data[key] = value
        contract.append("properties", row_data)

    contract.flags.ignore_mandatory = True
    contract.insert()

    return contract.name


@frappe.whitelist()
def make_customer(name):
    """Create a customer from the Utility Service Request."""
    doc = frappe.get_doc("Utility Service Request", name)
    customer_doc = create_customer(doc)
    frappe.db.set_value("Utility Service Request", name, "customer", customer_doc.name)
    frappe.db.set_value("Utility Service Request", name, "customer_name", customer_doc.customer_name)
    return customer_doc.name


def create_customer(doc):
    if doc.customer:
        return frappe.get_doc("Customer", doc.customer)
    
    from erpnext.selling.doctype.quotation.quotation import create_customer_from_lead, create_customer_from_prospect
    from crm.fcrm.doctype.erpnext_crm_settings.erpnext_crm_settings import create_customer_in_erpnext

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
    
    elif doc.service_request_from == "CRM Deal":
        existing_customer = frappe.db.get_value("Customer", {"crm_deal": doc.party_name}, "name")
        if not existing_customer:
            deal = frappe.get_doc("CRM Deal", doc.party_name)
            deal.status = "Won"
            deal.save()
            create_customer_in_erpnext(deal, None)
        existing_customer = frappe.db.get_value("Customer", {"crm_deal": doc.party_name}, "name")
        return frappe.get_doc("Customer", existing_customer)
    
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
    issue_doc.customer = doc.customer
    issue_doc.utility_property = doc.utility_property

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
def create_sales_order_doc(
    docname: str,
    items: list | str,
    customer: str = None,
    customer_name: str = None,
    transaction_date: str = None,
    company: str = None,
    property: str = None,
    enable_auto_repeat: str = None,
    adjustment_rule: str = None,
    start_date: str = None,
    end_date: str = None
):
    """
    Creates a Sales Order from a Utility Service Request and optionally creates an Auto Repeat document
    with contract details stored in the Auto Repeat document.

    :param docname: Utility Service Request name (str)
    :param items: List of item dictionaries (list or JSON string)
                  Each item dictionary must contain 'item_code', 'qty', and 'rate'.
    :param customer: Customer ID (str, optional)
    :param customer_name: Customer Name (str, optional)
    :param transaction_date: Sales Order date (str, optional). If not provided,
                             will attempt to use 'start_date' from utility property line.
    :param company: Company (str, optional)
    :param property: Utility Property name (str, optional)
    :param enable_auto_repeat: Flag to enable auto repeat ('1' for true, others for false) (str, optional)
    :param adjustment_rule: Name of the Billing Adjustment Rule to use (str, optional).
                            If not provided, will attempt to use from utility property line.
    :param start_date: Auto Repeat start date (str, optional). If not provided,
                       will attempt to use 'start_date' from utility property line.
    :param end_date: Auto Repeat end date (str, optional). If not provided,
                     will attempt to use 'end_date' from utility property line.
    :return: The name of the created Sales Order (str)
    :raises frappe.ValidationError: If items are not valid or required fields are missing.
    """
    items = _validate_items(items)
    usr, property_line, final_transaction_date, final_start_date, final_end_date = \
        _get_common_doc_details(docname, property, transaction_date, start_date, end_date)

    so = frappe.get_doc({
        "doctype": "Sales Order",
        "utility_service_request": docname,
        "customer": customer or usr.customer,
        "customer_name": customer_name or usr.customer_name,
        "transaction_date": final_transaction_date,
        "delivery_date": add_days(final_transaction_date, 7),
        "company": company or usr.company,
        "items": []
    })

    for item_data in items:
        so.append("items", {
            "item_code": item_data.get("item_code"),
            "qty": item_data.get("qty"),
            "rate": item_data.get("rate"),
            "uom": item_data.get("uom"),
            "amount": item_data.get("amount")
        })
    so.insert()

    _handle_auto_repeat(so, usr, property_line, enable_auto_repeat, adjustment_rule, final_start_date, final_end_date)

    return so.name

@frappe.whitelist()
def create_sales_invoice_doc(
    docname: str,
    items: list | str,
    customer: str = None,
    customer_name: str = None,
    posting_date: str = None,
    due_date: str = None,
    company: str = None,
    property: str = None,
    enable_auto_repeat: str = None,
    adjustment_rule: str = None,
    start_date: str = None,
    end_date: str = None
):
    """
    Creates a Sales Invoice from a Utility Service Request and optionally creates an Auto Repeat document
    with rent increment details stored in the Auto Repeat document.

    :param docname: Utility Service Request name (str)
    :param items: List of item dictionaries (list or JSON string)
                  Each item dictionary must contain 'item_code', 'qty', and 'rate'.
    :param customer: Customer ID (str, optional)
    :param customer_name: Customer Name (str, optional)
    :param posting_date: Sales Invoice posting date (str, optional). If not provided,
                         will attempt to use 'start_date' from utility property line.
    :param due_date: Sales Invoice due date (str, optional).
    :param company: Company (str, optional)
    :param property: Utility Property name (str, optional)
    :param enable_auto_repeat: Flag to enable auto repeat ('1' for true, others for false) (str, optional)
    :param adjustment_rule: Name of the Billing Adjustment Rule to use (str, optional).
                            If not provided, will attempt to use from utility property line.
    :param start_date: Auto Repeat start date (str, optional). If not provided,
                       will attempt to use 'start_date' from utility property line.
    :param end_date: Auto Repeat end date (str, optional). If not provided,
                     will attempt to use 'end_date' from utility property line.
    :return: The name of the created Sales Invoice (str)
    :raises frappe.ValidationError: If items are not valid or required fields are missing.
    """
    items = _validate_items(items)
    usr, property_line, final_posting_date, final_start_date, final_end_date = \
        _get_common_doc_details(docname, property, posting_date, start_date, end_date) 

    si = frappe.get_doc({
        "doctype": "Sales Invoice",
        "utility_service_request": docname,
        "customer": customer or usr.customer,
        "customer_name": customer_name or usr.customer_name,
        "posting_date": final_posting_date,
        "due_date": due_date,
        "company": company or usr.company,
        "set_draft_from_utility_service_request": 1,
        "items": []
    })

    for item_data in items:
        si.append("items", {
            "item_code": item_data.get("item_code"),
            "qty": item_data.get("qty"),
            "rate": item_data.get("rate"),
            "uom": item_data.get("uom"),
            "amount": item_data.get("amount")
        })
    si.insert()

    _handle_auto_repeat(si, usr, property_line, enable_auto_repeat, adjustment_rule, final_start_date, final_end_date)

    return si.name

def _validate_items(items):
    if isinstance(items, str):
        try:
            items = json.loads(items)
        except json.JSONDecodeError:
            frappe.throw("Items must be a valid JSON string or a list of item dictionaries.")

    if not isinstance(items, list):
        frappe.throw("Items must be a list of item dictionaries.")

    for item in items:
        if not isinstance(item, dict):
            frappe.throw("Each item in the 'items' list must be a dictionary.")
        if not item.get("item_code"):
            frappe.throw("Item Code is required for all items.")
        if item.get("qty") is None:
            frappe.throw("Quantity is required for all items.")
        if item.get("rate") is None:
            frappe.throw("Rate is required for all items.")
    return items

def _get_common_doc_details(docname, property, transaction_date, start_date, end_date):
    usr = frappe.get_doc("Utility Service Request", docname)

    property_line = None
    if property:
        property_line = next(
            (prop for prop in usr.requested_properties
             if prop.utility_property == property),
            None
        )

    primary_date = transaction_date or (property_line.start_date if property_line else None) or nowdate()
    final_start_date = start_date or (property_line.start_date if property_line else None) or nowdate()
    final_end_date = end_date or (property_line.end_date if property_line else None)

    return usr, property_line, primary_date, final_start_date, final_end_date

def _handle_auto_repeat(doc, usr, property, enable_auto_repeat, adjustment_rule, start_date, end_date):
    if enable_auto_repeat == "1":
        actual_adjustment_rule_name = adjustment_rule or (property.adjustment_rule if property else None)

        if actual_adjustment_rule_name:
            adjustment_rule_doc = frappe.get_doc("Billing Adjustment Rule", actual_adjustment_rule_name)

            auto_repeat_settings = {
                "frequency": adjustment_rule_doc.frequency,
                "start_date": start_date,
                "end_date": end_date,
                "utility_property": property.utility_property if property else None, # Pass the utility_property name
                "submit_on_creation": adjustment_rule_doc.submit_on_creation,
                "repeat_on_day": adjustment_rule_doc.repeat_on_day,
                "repeat_on_last_day": adjustment_rule_doc.repeat_on_last_day,
                "repeat_on_days": adjustment_rule_doc.repeat_on_days,
            }

            create_single_auto_repeat_with_contract_details(
                doc,
                usr,
                adjustment_rule_doc,
                auto_repeat_settings
            )

            add_transaction_comments(doc, usr.name, auto_repeat_settings)
        else:
            frappe.msgprint("Auto Repeat not created: No adjustment rule specified for property.")


def add_transaction_comments(transaction, usr_name, auto_repeat=None):
    """
    Add comprehensive comments to Utility Service Request and associated Utility Property
    documenting the transaction creation and auto-repeat setup.
    
    Args:
        transaction (Document): The created transaction document (Sales Order or Sales Invoice)
        usr_name (str): Name of the Utility Service Request
        auto_repeat (dict): Auto repeat configuration if applicable
    """
    def create_comment_content(title, doc, show_property=True, show_request_link=False):
        """Helper function to generate standardized comment content"""
        doc_type = doc.doctype
        doc_name = doc.name
        customer = doc.customer
        customer_name = doc.customer_name
        amount = doc.grand_total if hasattr(doc, 'grand_total') else doc.base_grand_total
        date_field = 'posting_date' if doc_type == 'Sales Invoice' else 'transaction_date'
        date_value = doc.get_formatted(date_field)
        
        content = f"""
        <div class='small'>
            <strong>{title}:</strong> 
            <a href='/app/{doc_type.lower().replace(" ", "-")}/{doc_name}'>{doc_name}</a>
            <br>
            <strong>Customer:</strong> 
            <a href='/app/customer/{customer}'>{customer_name}</a>
            <br>
            <strong>Amount:</strong> {amount}
            <br>
            <strong>{date_field.title()}:</strong> {date_value}
        """
        
        if show_request_link:
            content += f"""
            <br>
            <strong>From Request:</strong> 
            <a href='/app/utility-service-request/{usr_name}'>{usr_name}</a>
            """
        
        if show_property and auto_repeat and auto_repeat.get("utility_property"):
            property_name = frappe.db.get_value("Utility Property", 
                                              auto_repeat.get("utility_property"), 
                                              "property_name")
            content += f"""
            <br>
            <strong>Property:</strong> 
            <a href='/app/utility-property/{auto_repeat.get("utility_property")}'>
                {property_name or auto_repeat.get("utility_property")}
            </a>
            """
        
        if doc.get("auto_repeat"):
            auto_repeat_name = frappe.db.get_value("Auto Repeat", doc.auto_repeat, "name")
            content += f"""
            <br>
            <strong>Recurring {doc_type}:</strong> 
            <a href='/app/auto-repeat/{doc.auto_repeat}'>{auto_repeat_name}</a>
            <br>
            <strong>Frequency:</strong> {auto_repeat.get("frequency") if auto_repeat else ""}
            """
        
        content += "</div>"
        return content

    # Add comment to Utility Service Request
    usr_comment = create_comment_content(f"Created {transaction.doctype}", transaction)
    add_comment("Utility Service Request", usr_name, usr_comment)

    # Add comment to Utility Property if associated
    if auto_repeat and auto_repeat.get("utility_property"):
        property_comment = create_comment_content(
            f"{transaction.doctype} Created", 
            transaction, 
            show_property=False,
            show_request_link=True
        )
        add_comment("Utility Property", auto_repeat.get("utility_property"), property_comment)

def create_single_auto_repeat_with_contract_details(doc, usr, adjustment_rule, auto_repeat):
    """
    Creates an Auto Repeat document for a transaction (Sales Order or Sales Invoice) with comprehensive contract details,
    including increment settings from the associated property.
    
    Args:
        doc (Document): The document to be auto-repeated (Sales Order or Sales Invoice)
        usr (Utility Service Request): The parent request containing property details
        auto_repeat (dict): Configuration for the auto-repeat including:
            - frequency: Daily/Weekly/Monthly/Yearly
            - start_date: When billing should begin
            - end_date: Contractual end date (optional)
            - utility_property: Property ID for increment settings lookup
            - other auto-repeat settings (submit_on_creation, repeat_on_day etc.)
    
    Returns:
        None: Creates the Auto Repeat document directly
    """
    from frappe.utils import getdate, add_months
    
    # Get the specific property configuration from Utility Service Request
    property_doc = next(
        (prop for prop in usr.requested_properties 
         if prop.utility_property == auto_repeat.get("utility_property")),
        None
    )
    
    # Extract increment settings from property with fallback to 0 if not set
    increment_interval = adjustment_rule.increment_interval_months if property_doc else 0
    increment_percent = adjustment_rule.increment_percentage if property_doc else 0
    has_increment = increment_interval > 0 and increment_percent > 0
    
    # Date calculations for billing intervals
    start_date = getdate(auto_repeat.get("start_date"))  # First billing date
    contract_end_date = getdate(auto_repeat.get("end_date")) if auto_repeat.get("end_date") else None
    
    # Determine Auto Repeat end date:
    if has_increment:
        interval_end_date = add_months(start_date, float(increment_interval))
        if adjustment_rule.effective_after_months and float(adjustment_rule.effective_after_months) > 0:
            interval_end_date = add_months(start_date, float(adjustment_rule.effective_after_months))
        
        if contract_end_date and interval_end_date > contract_end_date:
            end_date = contract_end_date
        else:
            end_date = interval_end_date
    else:
        end_date = contract_end_date
    
    # Create the Auto Repeat document
    repeat_doc = frappe.get_doc({
        "doctype": "Auto Repeat",
        "reference_doctype": doc.doctype,
        "reference_document": doc.name,
        "frequency": auto_repeat.get("frequency"),
        "start_date": start_date,
        "end_date":  add_days(end_date, -1),
        "next_schedule_date": start_date,
        "submit_on_creation": auto_repeat.get("submit_on_creation", 1),
        "notify_by_email": 0,
        "repeat_on_day": auto_repeat.get("repeat_on_day"),
        "repeat_on_last_day": auto_repeat.get("repeat_on_last_day"),
        "auto_repeat_on_days": auto_repeat.get("repeat_on_days", []),
        
        # Contract metadata
        "contract_start_date": start_date,
        "contract_end_date": contract_end_date,
        "adjustment_rule": adjustment_rule.name,
        "enable_increment": 1 if has_increment else 0, 
    })
    
    # Save the Auto Repeat and link it to the document
    repeat_doc.insert(ignore_permissions=True)
    doc.db_set("auto_repeat", repeat_doc.name)
    
    # User feedback with actionable link
    msg = (f"Created Auto Repeat <a href='/app/auto-repeat/{repeat_doc.name}'>{repeat_doc.name}</a> "
           f"for {doc.customer_name}'s {doc.doctype.lower()} {doc.name}")
    
    if has_increment:
        msg += (f"\n• First billing interval ends on {end_date} "
                f"(after {increment_interval} months)")
    if contract_end_date:
        msg += f"\n• Full contract term until {contract_end_date}"
    
    # frappe.msgprint(msg)

def add_comment(doctype, docname, content):
    """Helper function to add a comment to a document"""
    frappe.get_doc({
        "doctype": "Comment",
        "comment_type": "Info",
        "reference_doctype": doctype,
        "reference_name": docname,
        "content": content
    }).insert(ignore_permissions=True)