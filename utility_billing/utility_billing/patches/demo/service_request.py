import frappe
from typing import List, Dict, Any
from .utils import safe_insert_doc, safe_load_json
from datetime import timedelta
from frappe.utils import nowdate, add_months, getdate

def insert_insurances(insurances: List[Dict[str, Any]]) -> None:
    """Insert insurance records with error handling."""
    for insurance in insurances:
        safe_insert_doc(
            "Insurance",
            {
                "doctype": "Insurance",
                "insurance_provider": insurance.get("insurance_provider"),
                "insurance_type": insurance.get("insurance_type"),
                "premium_price": insurance.get("premium_price"),
                "policy_number": insurance.get("policy_number"),
                "effective_date": insurance.get("effective_date"),
                "expiration_date": insurance.get("expiration_date"),
                "description": insurance.get("description"),
                "enabled": 1,
            },
            unique_key="policy_number"
        )


def insert_billing_adjustment_rules(billing_adjustment_rules: List[Dict[str, Any]]) -> None:
    """Insert billing adjustment rules with error handling."""
    for rule in billing_adjustment_rules:
        safe_insert_doc(
            "Billing Adjustment Rule",
            {
                "doctype": "Billing Adjustment Rule",
                "rule_name": rule.get("rule_name"),
                "frequency": rule.get("frequency"),
                "repeat_on_day": rule.get("repeat_on_day"),
                "overdue_after_days": rule.get("overdue_after_days"),
                "increment_interval_months": rule.get("increment_interval_months"),
                "increment_percentage": rule.get("increment_percentage"),
                "adjustment_cap": rule.get("adjustment_cap"),
                "adjustment_basis": rule.get("adjustment_basis"),
                "effective_after_months": rule.get("effective_after_months"),
                "penalty_type": rule.get("penalty_type"),
                "penalty_value": rule.get("penalty_value"),
                "penalty_frequency": rule.get("penalty_frequency"),
                "grace_period_days": rule.get("grace_period_days"),
                "penalty_cap": rule.get("penalty_cap"),
                "is_compounding": rule.get("is_compounding"),
                "disabled": rule.get("disabled"),
            },
            unique_key="rule_name"
        )


def insert_bill_structures(bill_structures: List[Dict[str, Any]]) -> None:
    """Insert utility bill structures with the latest fiscal year."""
    fiscal_years = frappe.get_list("Fiscal Year", 
                                  filters={"disabled": 0},
                                  order_by="year_start_date desc",
                                  limit=1)
    fiscal_year = fiscal_years[0].name if fiscal_years else None
    
    for structure in bill_structures:
        doc = frappe.get_doc({
            "doctype": "Utility Bill Structure",
            "fiscal_year": fiscal_year,
            "items": []
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
    existing_contracts = frappe.get_all("Contract", filters={"docstatus": 1})
    for contract in existing_contracts:
        doc = frappe.get_doc("Contract", contract.name)
        doc.flags.ignore_permissions = True
        if doc.docstatus == 1:
            doc.cancel()
        frappe.delete_doc("Contract", doc.name, force=1, ignore_permissions=True)

def get_random_bill_structure() -> str:
    """Fetch a random bill structure if available."""
    structures = frappe.get_list(
        "Utility Bill Structure",
        filters={"docstatus": 1},
        fields=["name"],
        limit=1,
        order_by="RAND()"
    )
    return structures[0].name if structures else None

def assign_properties_to_request(doc, requested_props: List[Dict[str, Any]], service_start, service_end, is_signed: bool) -> None:
    """Assign utility properties with calculated dates and status."""
    total_props = len(requested_props)
    if not total_props:
        return

    total_days = (service_end - service_start).days
    days_per_prop = total_days // total_props

    for i, prop in enumerate(requested_props):
        prop_start = service_start + timedelta(days=i * days_per_prop)
        prop_end = prop_start + timedelta(days=days_per_prop - 1)
        if prop_end > service_end:
            prop_end = service_end

        doc.append("requested_properties", {
            "utility_property": prop.get("utility_property"),
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

def insert_service_requests(service_requests: List[Dict[str, Any]]) -> None:
    """Insert service request records with calculated property dates."""
    clear_existing_contracts()

    for request in service_requests:
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
        })

        assign_properties_to_request(doc, request.get("requested_properties", []), service_start, service_end, is_signed)
        apply_contract_terms(doc, request.get("contract_template"))

        doc.insert(ignore_permissions=True)
        doc.submit()

        if request.get("requested_properties"):
            create_and_finalize_contract(doc.name, is_signed, request.get("requested_properties"))



def structures_setup():
    data = safe_load_json("structures.json")

    insert_insurances(data["insurances"])
    insert_billing_adjustment_rules(data["billing_adjustment_rules"])
    insert_bill_structures(data["bill_structures"])
    insert_contract_terms(data["contract_terms"])


def service_request_setup():
    """
    Setup service request structures.
    """
    data = safe_load_json("service_request.json")
    
    insert_service_requests(data)
    
    
