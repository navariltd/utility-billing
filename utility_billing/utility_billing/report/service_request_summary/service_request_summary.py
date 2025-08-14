# Copyright (c) 2025, Navari Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import today, date_diff, flt
from collections import defaultdict
from datetime import datetime


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    # summary = get_report_summary(data, filters)
    
    # chart = get_chart_data(data, filters)
    
    return columns, data, None, None, None

def get_columns():
    return [
        {
            "label": _("Service Request"),
            "fieldname": "name",
            "fieldtype": "Link",
            "options": "Utility Service Request",
            "width": 200
        },
        {
            "label": _("Date"),
            "fieldname": "date",
            "fieldtype": "Date",
            "width": 150
        },
        {
            "label": _("Customer"),
            "fieldname": "customer",
            "fieldtype": "Link",
            "options": "Customer",
            "width": 150
        },
        {
            "label": _("Request Type"),
            "fieldname": "request_type",
            "fieldtype": "Link",
            "options": "Issue Type",
            "width": 150
        },
        # {
        #     "label": _("Status"),
        #     "fieldname": "status",
        #     "width": 120
        # },
        {
            "label": _("Request Status"),
            "fieldname": "request_status",
            "width": 150
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
            "label": _("Contract Length (Months)"),
            "fieldname": "contract_length_months",
            "fieldtype": "Float",
            "width": 150,
            "precision": 2
        },
        {
            "label": _("Properties Count"),
            "fieldname": "properties_count",
            "fieldtype": "Int",
            "width": 120
        },
        {
            "label": _("Company"),
            "fieldname": "company",
            "fieldtype": "Link",
            "options": "Company",
            "width": 120
        },
        {
            "label": _("Territory"),
            "fieldname": "territory",
            "fieldtype": "Link",
            "options": "Territory",
            "width": 120
        },
        {
            "label": _("Customer Group"),
            "fieldname": "customer_group",
            "fieldtype": "Link",
            "options": "Customer Group",
            "width": 150
        },
        {
            "label": _("Utility Bill Structure"),
            "fieldname": "utility_bill_structure",
            "fieldtype": "Link",
            "options": "Utility Bill Structure",
            "width": 180
        },
        {
            "label": _("Remarks"),
            "fieldname": "remarks",
            "width": 200
        }
    ]

def get_data(filters):
    conditions = get_conditions(filters)
    conditions.append(["docstatus", "=", 1])

    data = frappe.get_all(
        "Utility Service Request",
        filters=conditions,
        fields=[
            "name", "date", "customer", "customer_name", "request_type",
            "status", "request_status", "start_date", "end_date", "contract_length_months",
            "company", "territory", "customer_group", "utility_bill_structure",
            "remarks"
        ],
        order_by="date desc, name desc"
    )

    for row in data:
        row["properties_count"] = frappe.db.count(
            "Contract Utility Property Item",
            filters={"parent": row["name"]}
        )
        if row.get("start_date") and row.get("end_date"):
            row["remaining_days"] = date_diff(row["end_date"], today())
        else:
            row["remaining_days"] = 0

    return data


def get_conditions(filters):
    conditions = []
    
    if not isinstance(filters, dict):
        try:
            filters = frappe.parse_json(filters)
        except:
            filters = {}

    if filters.get("from_date"):
        conditions.append(["date", ">=", filters.get("from_date")])
    if filters.get("to_date"):
        conditions.append(["date", "<=", filters.get("to_date")])
    if filters.get("customer"):
        conditions.append(["customer", "=", filters.get("customer")])
    if filters.get("customer_group"):
        conditions.append(["customer_group", "=", filters.get("customer_group")])
    if filters.get("territory"):
        conditions.append(["territory", "=", filters.get("territory")])
    if filters.get("company"):
        conditions.append(["company", "=", filters.get("company")])
    if filters.get("status"):
        conditions.append(["status", "=", filters.get("status")])
    if filters.get("request_status"):
        conditions.append(["request_status", "=", filters.get("request_status")])
    if filters.get("request_type"):
        conditions.append(["request_type", "=", filters.get("request_type")])
    if filters.get("utility_bill_structure"):
        conditions.append(["utility_bill_structure", "=", filters.get("utility_bill_structure")])

    return conditions


def get_report_summary(data, filters):
    if not data:
        return []
    
    status_labels = {
        "Draft": _("Draft"),
        "On Hold": _("On Hold"),
        "To Pay": _("To Pay"),
        "To Bill": _("To Bill"),
        "To Deliver": _("To Deliver"),
        "Completed": _("Completed"),
        "Cancelled": _("Cancelled"),
        "Closed": _("Closed")
    }
    
    request_status_labels = {
        "Site Survey Created": _("Survey Created"),
        "Site Survey Completed": _("Survey Completed"),
        "BOM Created": _("BOM Created"),
        "BOM Completed": _("BOM Completed")
    }
    

    
    summary = []
    total = 0
    # total_amount = 0
    status_counts = {k: 0 for k in status_labels}
    request_status_counts = {k: 0 for k in request_status_labels}
    
    for d in data:
        status = d.get("status")
        request_status = d.get("request_status")
        
        if status in status_labels:
            status_counts[status] += 1
        if request_status in request_status_labels:
            request_status_counts[request_status] += 1
        
        total += 1
        # total_amount += flt(d.billed_amount)
    
    for key, label in status_labels.items():
        if status_counts[key] > 0:
            summary.append({
                "value": status_counts[key],
                "indicator": get_status_indicator(key),
                "label": label,
                "datatype": "Int"
            })
    
    for key, label in request_status_labels.items():
        if request_status_counts[key] > 0:
            summary.append({
                "value": request_status_counts[key],
                "indicator": "Blue",
                "label": label,
                "datatype": "Int"
            })
    
    
    summary.insert(0, {
        "value": total,
        "indicator": "Blue",
        "label": _("Total Requests"),
        "datatype": "Int"
    })
    
    # summary.insert(1, {
    #     "value": total_amount,
    #     "indicator": "Green",
    #     "label": _("Total Billed Amount"),
    #     "datatype": "Currency"
    # })
    
    return summary

def get_status_indicator(status):
    indicators = {
        "Draft": "Gray",
        "On Hold": "Orange",
        "To Pay": "Blue",
        "To Bill": "Yellow",
        "To Deliver": "Purple",
        "Completed": "Green",
        "Cancelled": "Red",
        "Closed": "Dark Grey"
    }
    return indicators.get(status, "Blue")


def get_chart_data(data, filters):
    if not data:
        return None
    
    charts = []

    status_data = defaultdict(int)
    for d in data:
        status = d.get("status")
        status_data[status] += 1

    if status_data:
        charts.append({
            "title": _("Status Distribution"),
            "data": {
                "labels": list(status_data.keys()),
                "datasets": [{
                    "name": _("Number of Requests"),
                    "values": list(status_data.values())
                }]
            },
            "type": "pie",
            "height": 300,
            "colors": ["#5e64ff", "#ffa00a", "#f86c6b", "#28a745", "#6c757d", "#17a2b8", "#fd7e14", "#6f42c1"]
        })

    billing_data = defaultdict(int)

    if billing_data:
        charts.append({
            "title": _("Billing Status"),
            "data": {
                "labels": list(billing_data.keys()),
                "datasets": [{
                    "name": _("Number of Requests"),
                    "values": list(billing_data.values())
                }]
            },
            "type": "pie",
            "height": 300,
            "colors": ["#6c757d", "#28a745", "#ffc107", "#dc3545"]
        })

    if filters.get("from_date") and filters.get("to_date"):
        try:
            from_date = datetime.strptime(filters["from_date"], "%Y-%m-%d").date()
            to_date = datetime.strptime(filters["to_date"], "%Y-%m-%d").date()
        except ValueError:
            return charts[0] if charts else None

        monthly_count = defaultdict(int)
        monthly_amount = defaultdict(float)

        for d in data:
            date_str = d.get("date")
            try:
                entry_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except (TypeError, ValueError):
                continue

            if from_date <= entry_date <= to_date:
                month_key = entry_date.strftime("%Y-%m")
                monthly_count[month_key] += 1
                # monthly_amount[month_key] += float(d.get("billed_amount") or 0)

        if monthly_count:
            months = sorted(monthly_count.keys())
            counts = [monthly_count[month] for month in months]
            amounts = [monthly_amount[month] for month in months]

            charts.append({
                "title": _("Monthly Trend"),
                "data": {
                    "labels": months,
                    "datasets": [
                        {
                            "name": _("Number of Requests"),
                            "values": counts,
                            "chartType": "bar"
                        },
                        {
                            "name": _("Billed Amount"),
                            "values": amounts,
                            "chartType": "line"
                        }
                    ]
                },
                "type": "axis-mixed",
                "height": 300,
                "colors": ["#5e64ff", "#ffa00a"]
            })

    return charts[0] if charts else None

    return [
        {
            "fieldname": "from_date",
            "label": _("From Date"),
            "fieldtype": "Date",
            "width": "80",
            "default": frappe.datetime.add_months(today(), -1)
        },
        {
            "fieldname": "to_date",
            "label": _("To Date"),
            "fieldtype": "Date",
            "width": "80",
            "default": today()
        },
        {
            "fieldname": "customer",
            "label": _("Customer"),
            "fieldtype": "Link",
            "options": "Customer",
            "width": "120"
        },
        {
            "fieldname": "customer_group",
            "label": _("Customer Group"),
            "fieldtype": "Link",
            "options": "Customer Group",
            "width": "120"
        },
        {
            "fieldname": "territory",
            "label": _("Territory"),
            "fieldtype": "Link",
            "options": "Territory",
            "width": "120"
        },
        {
            "fieldname": "company",
            "label": _("Company"),
            "fieldtype": "Link",
            "options": "Company",
            "width": "120"
        },
        {
            "fieldname": "status",
            "label": _("Status"),
            "fieldtype": "Select",
            "options": "\nDraft\nOn Hold\nTo Pay\nTo Bill\nTo Deliver\nCompleted\nCancelled\nClosed",
            "width": "120"
        },
        {
            "fieldname": "request_status",
            "label": _("Request Status"),
            "fieldtype": "Select",
            "options": "\nSite Survey Created\nSite Survey Completed\nBOM Created\nBOM Completed",
            "width": "150"
        },
        {
            "fieldname": "request_type",
            "label": _("Request Type"),
            "fieldtype": "Link",
            "options": "Issue Type",
            "width": "150"
        },
        {
            "fieldname": "utility_bill_structure",
            "label": _("Utility Bill Structure"),
            "fieldtype": "Link",
            "options": "Utility Bill Structure",
            "width": "150"
        }
    ]