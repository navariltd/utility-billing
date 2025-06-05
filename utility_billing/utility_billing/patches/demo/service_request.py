import frappe
from typing import List, Dict, Any
from .utils import safe_insert_doc, safe_load_json


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


def structures_setup():
    data = safe_load_json("structures.json")

    insert_insurances(data["insurances"])
    insert_billing_adjustment_rules(data["billing_adjustment_rules"])
    insert_bill_structures(data["bill_structures"])
