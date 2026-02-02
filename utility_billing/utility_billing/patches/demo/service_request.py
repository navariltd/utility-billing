import frappe
import random
from typing import List, Dict, Any
from .utils import safe_insert_doc, safe_load_json
from datetime import timedelta
from frappe.utils import nowdate, add_months, getdate


def clear_bill_structures() -> None:
    docs = frappe.get_list("Utility Bill Structure", 
                          filters={"company": "Utility and Rental (Demo)"}, 
                          fields=["name"])

    for d in docs:
        try:
            doc = frappe.get_doc("Utility Bill Structure", d.name)
            if doc.docstatus == 1:
                doc.cancel()
            doc.delete()
        except Exception as e:
            frappe.log_error(f"Error deleting {d.name}: {str(e)}", "clear_all_bill_structures")

    frappe.db.commit()


def insert_bill_structures() -> None:
    """Insert utility bill structures with the latest fiscal year.""" 
    bill_structures = safe_load_json("data/utility_bill_structure.json")
    fiscal_years = frappe.get_list("Fiscal Year", 
                                  filters={"disabled": 0},
                                  order_by="year_start_date desc",
                                  limit=1)
    fiscal_year = fiscal_years[0].name if fiscal_years else None
    
    for structure in bill_structures:
        doc = frappe.get_doc({
            "doctype": "Utility Bill Structure",
            "fiscal_year": fiscal_year,
            "items": [],
            "company": structure.get("company", "Utility and Rental (Demo)"),
        })
        
        for item in structure.get("items", []):
            doc.append("items", {
                "item": item.get("item"),
                "amount": item.get("amount"),
                "total": item.get("total")
            })
        
        doc.insert(ignore_permissions=True)
        doc.submit()


def insert_contract_terms(contract_terms: List[Dict[str, Any]]) -> None:
    """Insert contract terms with error handling."""
    for term in contract_terms:
        safe_insert_doc(
            "Contract Template",
            {
                "doctype": "Contract Template",
                "title": term.get("title"),
                "contract_terms": term.get("contract_terms"),
            },
            unique_key="title"
        )
        

def clear_existing_contracts() -> None:
    """Cancel and delete all submitted contracts."""
    customers_data = safe_load_json("data/customer.json")
    demo_parties = [c["customer_name"] for c in customers_data]
    
    if not demo_parties:
        return

    demo_contracts = {
        contract.name: contract for contract in frappe.get_all(
            "Contract",
            filters={"party_name": ["in", demo_parties]},
            fields=["name", "docstatus", "party_name"]
        )
    }

    if not demo_contracts:
        return

    deleted_count = 0
    for contract_name, contract in demo_contracts.items():
        try:
            if contract.docstatus == 1:  
                contract_doc = frappe.get_doc("Contract", contract_name)
                contract_doc.cancel()
                frappe.db.commit()
            
            frappe.delete_doc("Contract", contract_name)
            frappe.db.commit()
            deleted_count += 1
        except Exception as e:
            frappe.db.rollback()
            frappe.log_error(f"Failed to delete Contract {contract_name}: {str(e)}")


def get_random_bill_structure() -> str:
    """Fetch a random bill structure if available."""
    structures = frappe.get_list(
        "Utility Bill Structure",
        filters={"docstatus": 1},
        fields=["name"],
    )

    if not structures:
        return

    return random.choice(structures).name

def assign_properties_to_request(doc, requested_props: List[Dict[str, Any]], service_start, service_end, is_signed: bool) -> None:
    """Assign utility properties with calculated dates and status."""
    total_props = len(requested_props)
    if not total_props:
        return

    total_days = (service_end - service_start).days
    days_per_prop = total_days // total_props
    
    def get_random_insurance():
        """Fetch a random insurance policy if available."""
        total = frappe.db.count("Insurance")

        if not total:
            return None

        offset = random.randint(0, total - 1)

        insurances = frappe.get_list(
            "Insurance",
            fields=["name"],
            start=offset,
            limit=1
        )

        return insurances[0].name if insurances else None

    for i, prop in enumerate(requested_props):
        prop_start = service_start + timedelta(days=i * days_per_prop)
        prop_end = prop_start + timedelta(days=days_per_prop - 1)
        if prop_end > service_end:
            prop_end = service_end
            
        insurance = get_random_insurance() 

        doc.append("requested_properties", {
            "utility_property": prop.get("utility_property"),
            "insurance": insurance,
            "start_date": prop_start,
            "end_date": prop_end,
            "adjustment_rule": prop.get("adjustment_rule"),
            "status": "Occupied" if is_signed else "Reserved"
        })

def apply_contract_terms(doc, template_name: str) -> None:
    """Copy contract terms from template."""
    if not template_name:
        return
    template_doc = frappe.get_doc("Contract Template", template_name)
    if template_doc and template_doc.contract_terms:
        doc.contract_terms = template_doc.contract_terms
        
def create_and_finalize_contract(service_request_name: str, is_signed: bool, properties: List) -> None:
    """Create, submit, and optionally sign the associated contract."""
    from utility_billing.utility_billing.doctype.utility_service_request.utility_service_request import create_contract
    contract_name = create_contract(service_request_name)
    contract = frappe.get_doc("Contract", contract_name)
    contract.save(ignore_permissions=True)
    contract.submit()
    
    status = "Occupied" if is_signed else "Reserved"
    for prop in properties:
        if prop.get("utility_property"):
            try:
                property_doc = frappe.get_doc("Utility Property", prop.get("utility_property"))
                property_doc.status = status
                property_doc.save(ignore_permissions=True)
            except Exception as e:
                frappe.log_error(f"Failed to update property status: {str(e)}")
    
    if is_signed:
        contract.is_signed = 1
        contract.save(ignore_permissions=True)

def insert_service_requests() -> None:
    """Insert service request records with calculated property dates."""
    service_requests = safe_load_json("data/utility_service_request.json")
    
    for request in service_requests:
        try:
            service_start = getdate(nowdate())
            contract_length = request.get("contract_length_months", 12)
            service_end = add_months(service_start, contract_length)

            bill_structure = get_random_bill_structure()
            is_signed = request.get("is_signed", False)

            doc = frappe.get_doc({
                "doctype": "Utility Service Request",
                "request_type": request.get("request_type"),
                "party_name": request.get("party_name"),
                "customer_group": request.get("customer_group"),
                "start_date": service_start,
                "contract_length_months": contract_length,
                "contract_template": request.get("contract_template"),
                "utility_bill_structure": bill_structure,
                "company": "Utility and Rental (Demo)"
            })

            assign_properties_to_request(doc, request.get("requested_properties", []), service_start, service_end, is_signed)
            apply_contract_terms(doc, request.get("contract_template"))

            doc.insert(ignore_permissions=True)
            doc.submit()

            if request.get("requested_properties"):
                create_and_finalize_contract(doc.name, is_signed, request.get("requested_properties"))
        except Exception as e:
            frappe.log_error(
                "insert_service_requests",
                f"Error creating service request for {request.get('party_name')}: {str(e)}",
            )
 
def clear_service_requests() -> None:
    """
    Cancel and delete demo Utility Service Requests and their linked Sales Invoices
    """
    service_requests_data = safe_load_json("data/utility_service_request.json")
    if not service_requests_data:
        return

    demo_parties = list({req["party_name"] for req in service_requests_data if req.get("party_name")})
    
    if not demo_parties:
        return

    demo_requests = frappe.get_all(
        "Utility Service Request",
        filters={"party_name": ["in", demo_parties]},
        fields=["name", "docstatus"]
    )

    for req in demo_requests:
        invoices = frappe.get_all(
            "Sales Invoice",
            filters={"utility_service_request": req.name},
            fields=["name", "docstatus"]
        )
        
        for invoice in invoices:
            try:
                auto_repeats = frappe.get_all(
                    "Auto Repeat",
                    filters={"reference_doctype": "Sales Invoice", "reference_document": invoice.name},
                    fields=["name"]
                )

                for ar in auto_repeats:
                    try:
                        ar_doc = frappe.get_doc("Auto Repeat", ar.name)
                        if ar_doc.docstatus == 1:
                            ar_doc.cancel()
                        frappe.delete_doc("Auto Repeat", ar.name)
                    except Exception as e:
                        frappe.db.rollback()
                        frappe.log_error(f"Error handling Auto Repeat for Sales Invoice {invoice.name}: {e}")                
                
                if invoice.docstatus == 1:
                    inv_doc = frappe.get_doc("Sales Invoice", invoice.name)
                    inv_doc.cancel()
                
                frappe.delete_doc("Sales Invoice", invoice.name)
            except Exception as e:
                frappe.log_error(
                    title="Sales Invoice Deletion Failed",
                    message=f"Invoice: {invoice.name}, Service Request: {req.name}\nError: {str(e)}"
                )

    deleted_count = 0
    for req in demo_requests:
        try:
            if req.docstatus == 1:
                frappe.get_doc("Utility Service Request", req.name).cancel()

            frappe.delete_doc("Utility Service Request", req.name)
            deleted_count += 1

        except Exception as e:
            frappe.log_error(
                title="Service Request Deletion Failed",
                message=f"Request: {req.name}\nError: {str(e)}"
            )




    
    
