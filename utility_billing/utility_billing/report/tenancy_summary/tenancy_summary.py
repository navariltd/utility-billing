# Copyright (c) 2025, Navari Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate, today, date_diff, flt

from utility_billing.utility_billing.utils.release import FIELD as RELEASED_ON
from utility_billing.utility_billing.utils.release import contract_row_release, owned_period, release_dates_stored
from utility_billing.utility_billing.utils.request_prices import is_item_price_approach

def execute(filters=None):
    columns = get_columns()
    if is_item_price_approach():
        # A released row holds its property up to and including this date
        columns.insert(
            [column["fieldname"] for column in columns].index("is_active") + 1,
            {"label": _("Released On"), "fieldname": "released_on", "fieldtype": "Date", "width": 110},
        )
    data = get_data(filters)
    summary = get_report_summary(data)
    chart = get_chart_data(data)
    
    return columns, data, None, chart, summary

def get_columns():
    return [
        {
            "label": _("Contract"),
            "fieldname": "contract",
            "fieldtype": "Link",
            "options": "Contract",
            "width": 200
        },
        {
            "label": _("Status"),
            "fieldname": "status",
            "width": 120
        },
        {
            "label": _("Customer"),
            "fieldname": "customer",
            "fieldtype": "Link",
            "options": "Customer",
            "width": 160
        },
        {
            "label": _("Property"),
            "fieldname": "property",
            "fieldtype": "Link",
            "options": "Utility Property",
            "width": 120
        },
        {
            "label": _("Start Date"),
            "fieldname": "start_date",
            "fieldtype": "Date",
            "width": 100
        },
        {
            "label": _("End Date"),
            "fieldname": "end_date",
            "fieldtype": "Date",
            "width": 100
        },
        {
            "label": _("Active"),
            "fieldname": "is_active",
            "fieldtype": "Check",
            "width": 80
        },
        {
            "label": _("Contract Length (Months)"),
            "fieldname": "contract_length",
            "fieldtype": "Float",
            "width": 120,
            "precision": 2
        },
        {
            "label": _("Remaining Days"),
            "fieldname": "remaining_days",
            "fieldtype": "Int",
            "width": 120
        },
        {
            "label": _("Adjustment Rule"),
            "fieldname": "adjustment_rule",
            "fieldtype": "Link",
            "options": "Billing Adjustment Rule",
            "width": 150
        },
        {
            "label": _("Insurance"),
            "fieldname": "insurance",
            "fieldtype": "Link",
            "options": "Insurance",
            "width": 120
        },
    ]

def get_data(filters):
    contract_filters = {"docstatus": 1}

    if filters.get("customer"):
        contract_filters["party_name"] = filters.get("customer")

    if filters.get("status") and filters.get("status") not in ("Nearing End",):
        contract_filters["status"] = filters.get("status")

    if filters.get("company"):
        service_requests = frappe.get_all(
            "Utility Service Request",
            filters={"company": filters.get("company")},
            fields=["name"]
        )
        
        if not service_requests:
            return []
        
        sr_names = [sr.name for sr in service_requests]
        contracts_with_sr = frappe.get_all(
            "Contract",
            filters={
                "utility_service_request": ["in", sr_names],
                "docstatus": 1
            },
            fields=["name"]
        )
        
        if not contracts_with_sr:
            return []
            
        contract_filters["name"] = ["in", [c.name for c in contracts_with_sr]]

    contracts = frappe.get_all(
        "Contract",
        filters=contract_filters,
        fields=["name", "party_name as customer", "start_date", "end_date", "status"],
        order_by="party_name, start_date"
    )

    months_in_advance = frappe.db.get_single_value(
        "Utility Billing Settings", "months_in_advance_to_notify_of_tenancy_ending"
    ) or 6
    days_threshold = int(months_in_advance * 30)

    data = []
    # Under Item Price a row released on the Contract holds its property up to and
    # including its Released On: its end, remaining days and Active filter follow it
    item_price = is_item_price_approach()
    wanted_status = filters.get("property_status") or None

    for contract in contracts:
        prop_filters = {"parent": contract.name}

        for key in ("property", "property_status"):
            filter_value = filters.get(key)
            if key == "property_status":
                if filter_value == "" or filter_value is None or item_price:
                    continue  
                filter_value = 1 if filter_value == "Active" else 0
            if filter_value is not None:
                prop_filters["utility_property" if key == "property" else "is_active"] = filter_value

        properties = frappe.get_all(
            "Contract Utility Property Item",
            filters=prop_filters,
            fields=[
                "utility_property", "start_date", "end_date", 
                "is_active", "contract_length_months as contract_length", 
                "adjustment_rule", "insurance"
            ] + ([RELEASED_ON] if item_price and release_dates_stored() else [])
        )

        for prop in properties:
            released, released_on = contract_row_release(prop)
            prop.released_on = released_on
            prop.lease_end = prop.end_date
            prop.holding = bool(prop.is_active)
            if item_price and released:
                period = owned_period(prop.start_date, prop.end_date, True, released_on)
                prop.lease_end = period[1] if period else None
                prop.holding = bool(period) and getdate(period[1]) >= getdate(today())

        if item_price and wanted_status:
            properties = [prop for prop in properties if prop.holding == (wanted_status == "Active")]

        for idx, prop in enumerate(properties):
            if filters.get("from_date") and prop.lease_end and getdate(prop.lease_end) < getdate(filters.get("from_date")):
                continue
            if filters.get("to_date") and prop.start_date and getdate(prop.start_date) > getdate(filters.get("to_date")):
                continue

            remaining_days = 0
            if prop.lease_end:
                remaining_days = date_diff(prop.lease_end, today())

            row_status = contract.status if idx == 0 else ""
            if remaining_days > 0 and remaining_days <= days_threshold and contract.status == "Active":
                row_status = "Nearing End"

            if filters.get("status") == "Nearing End" and row_status != "Nearing End":
                continue

            data.append({
                "contract": contract.name if idx == 0 else "",
                "customer": contract.customer if idx == 0 else "",
                "property": prop.utility_property,
                "utility_property": prop.utility_property,
                "start_date": prop.start_date,
                "end_date": prop.end_date,
                "is_active": prop.is_active,
                "contract_length": flt(prop.contract_length),
                "remaining_days": remaining_days if prop.lease_end else None,
                **({"released_on": prop.released_on} if item_price else {}),
                "adjustment_rule": prop.adjustment_rule,
                "insurance": prop.insurance,
                "status": row_status,
                "indent": 1 if idx > 0 else 0
            })

    return data

def get_report_summary(data):
    if not data:
        return []

    status_labels = {
        "Active": _("Active"),
        "Nearing End": _("Nearing End"),
        "Expired": _("Expired"),
        "Cancelled": _("Cancelled"),
        "Draft": _("Draft"),
    }

    summary = []
    total = 0
    status_counts = {k: 0 for k in status_labels}

    for d in data:
        status = d.get("status")
        if status in status_labels:
            status_counts[status] += 1
            total += 1

    for key, label in status_labels.items():
        summary.append({
            "value": status_counts[key],
            "indicator": {
                "Active": "Green",
                "Nearing End": "Orange",
                "Expired": "Gray",
                "Cancelled": "Red",
                "Draft": "Blue"
            }[key],
            "label": label,
            "datatype": "Int"
        })

    summary.insert(0, {
        "value": total,
        "indicator": "Blue",
        "label": _("Total Properties"),
        "datatype": "Int"
    })

    return summary

def get_chart_data(data):
    if not data:
        return None
    
    status_data = {}
    status_colors = {
        "Active": "#28a745",    
        "Nearing End": "#ffa500", 
        "Expired": "#6c757d",   
        "Cancelled": "#dc3545", 
        "Draft": "#007bff"      
    }
    
    for d in data:
        if d.get("is_total"):
            continue
        status = d.get("status")
        if status:
            status_data[status] = status_data.get(status, 0) + 1
    
    labels = list(status_data.keys())
    colors = [status_colors.get(label, "#000000") for label in labels]
    
    chart = {
        "data": {
            "labels": labels,
            "datasets": [{
                "name": _("Contract Status"),
                "values": list(status_data.values())
            }]
        },
        "type": "pie",
        "height": 300,
        "colors": colors,
        "title": _("Contract Status Distribution")
    }
    
    return chart
