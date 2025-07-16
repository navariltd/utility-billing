import frappe
from frappe import _

@frappe.whitelist()
def update_billing_status(utility_service_request):
    doc = frappe.get_doc("Utility Service Request", utility_service_request)

    # Get submitted Sales Invoices linked to this request
    invoices = frappe.get_all("Sales Invoice", 
        filters={
            "docstatus": 1,
            "utility_service_request": utility_service_request
        },
        fields=["grand_total", "outstanding_amount"]
    )

    total_billed = sum(inv.grand_total for inv in invoices)
    total_outstanding = sum(inv.outstanding_amount for inv in invoices)
    total_amount = sum(item.amount for item in doc.items)

    # Calculate billed percent
    # billed_percent = round((total_billed / total_amount) * 100, 2) if total_amount else 0

    # Update fields
    # doc.billed_amount = total_billed
    doc.total_amount = total_amount
    # doc.per_billed = billed_percent

    # Determine billing status
    if doc.status == "Closed":
        doc.billing_status = "Closed"
    elif total_billed == 0:
        doc.billing_status = "Not Billed"
    elif total_billed < total_amount:
        doc.billing_status = "Partly Billed"
    else:
        doc.billing_status = "Fully Billed"

    # Determine status
    if doc.billing_status == "Closed":
        doc.status = "Closed"
    elif doc.status == "On Hold":
        pass  # Preserve manual hold
    elif doc.billing_status == "Fully Billed" and total_outstanding > 0:
        doc.status = "To Pay"
    elif doc.billing_status == "Not Billed":
        doc.status = "To Bill"
    elif doc.billing_status == "Partly Billed":
        doc.status = "To Bill"
    elif doc.billing_status == "Fully Billed":
        doc.status = "Completed"

    doc.save(ignore_permissions=True)
