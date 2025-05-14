import frappe
from frappe.query_builder import DocType
from frappe.utils import today, add_days, date_diff
from typing import List, Dict, Any, Optional

@frappe.whitelist()
def cancel_auto_repeats_for_property(property_name: str) -> None:
    SalesInvoice = DocType("Sales Invoice")
    SalesInvoiceItem = DocType("Sales Invoice Item")
    AutoRepeat = DocType("Auto Repeat")

    invoice_query = (
        frappe.qb.from_(SalesInvoice)
        .left_join(SalesInvoiceItem)
        .on(SalesInvoice.name == SalesInvoiceItem.parent)
        .select(SalesInvoice.name)
        .where(
            (SalesInvoice.utility_property == property_name)
            | (SalesInvoiceItem.utility_property == property_name)
        )
        .distinct()
    )
    invoice_names = [row[0] for row in invoice_query.run()]
    
    if not invoice_names:
        return

    auto_repeat_query = (
        frappe.qb.from_(AutoRepeat)
        .select(AutoRepeat.name, AutoRepeat.reference_document)
        .where(
            (AutoRepeat.reference_doctype == "Sales Invoice")
            & (AutoRepeat.reference_document.isin(invoice_names))
        )
    )
    auto_repeats = auto_repeat_query.run()
    for auto_repeat in auto_repeats:
        auto_repeat_name = auto_repeat[0]
        auto_repeat_doc = frappe.get_doc("Auto Repeat", auto_repeat_name)
        auto_repeat_doc.disabled = 1
        auto_repeat_doc.save()


@frappe.whitelist()
def process_penalties_for_overdue_invoices() -> None:
    # No params to check
    try:
        overdue_invoices = frappe.db.get_list("Sales Invoice", filters={"status": "Overdue"}, fields=["name", "due_date", "posting_date", "customer"])

        for invoice in overdue_invoices:
            try:
                original_invoice = frappe.get_doc("Sales Invoice", invoice["name"])
                service_request = original_invoice.get("utility_service_request")

                if not service_request:
                    continue

                service_request_doc = frappe.get_doc("Utility Service Request", service_request)
                requested_properties = service_request_doc.get("requested_properties")

                penalty_items = []

                for item in original_invoice.items:
                    try:
                        utility_property = item.utility_property

                        matching_request = next((req for req in requested_properties if req.utility_property == utility_property), None)
                        
                        if not matching_request or not matching_request.adjustment_rule:
                            continue

                        rule = frappe.get_doc("Billing Adjustment Rule", matching_request.adjustment_rule)
                        days_overdue = date_diff(today(), invoice["due_date"]) - float(rule.grace_period_days)
                        if days_overdue <= rule.grace_period_days:
                            continue

                        frequency_days = get_frequency_days(rule.penalty_frequency)
                        if frequency_days > 0:
                            penalty_cycles = max(1, days_overdue // frequency_days)
                            qty = penalty_cycles
                        else:
                            penalty_cycles = 1
                            qty = 1

                        penalty_amount = 0
                        rate = 0

                        if rule.penalty_type == "Fixed Amount":
                            rate = rule.penalty_value
                            penalty_amount = penalty_cycles * rule.penalty_value
                        elif rule.penalty_type == "Percentage":
                            base = item.amount
                            if rule.is_compounding:
                                for _ in range(penalty_cycles):
                                    increment = base * (rule.penalty_value / 100)
                                    penalty_amount += increment
                                    base += increment
                                rate = penalty_amount / qty if qty else penalty_amount
                            else:
                                rate = base * (rule.penalty_value / 100)
                                penalty_amount = rate * penalty_cycles

                        if rule.penalty_cap and penalty_amount > rule.penalty_cap:
                            penalty_amount = rule.penalty_cap
                            rate = penalty_amount / qty if qty else penalty_amount

                        if penalty_amount > 0:
                            penalty_items.append({
                                "item_code": item.item_code,
                                "description": f"Penalty for overdue invoice {invoice['name']}",
                                "qty": qty,
                                "rate": rate,
                                "amount": penalty_amount,
                                "income_account": rule.penalty_income_account,
                                "receivable_account": rule.penalty_receivable_account,
                                "utility_property": utility_property,
                            })
                            
                    except Exception as item_err:
                        frappe.log_error(f"Error processing item {item.item_code} in invoice {invoice['name']}: {frappe.get_traceback()}")
                if penalty_items:
                    try:
                        create_penalty_invoice(original_invoice, service_request, rule, penalty_items)
                    except Exception as create_err:
                        frappe.log_error(f"Error creating penalty invoice for {invoice['name']}: {frappe.get_traceback()}")

            except Exception as inv_err:
                frappe.log_error(f"Error processing invoice {invoice.get('name', '')}: {frappe.get_traceback()}")

    except Exception as e:
        frappe.log_error(f"Error in process_penalties_for_overdue_invoices: {frappe.get_traceback()}")
        

def get_frequency_days(frequency: str) -> int:
    return {
        "Daily": 1,
        "Weekly": 7,
        "Monthly": 30,
        "One-time": 0
    }.get(frequency, 1)
    

def create_penalty_invoice(
    original_invoice: Any,
    service_request: str,
    rule: Any,
    items: List[Dict[str, Any]]
) -> None:
    try:
        new_total = sum(float(item.get("amount") or 0) for item in items)
        penalty_remarks = f"Penalty Invoice for overdue invoice {original_invoice.name}"

        previous_penalties = frappe.get_all(
            "Sales Invoice",
            filters={"remarks": penalty_remarks},
            fields=["name", "creation"],
            order_by="creation desc"
        )

        latest_invoice = None

        for idx, penalty in enumerate(previous_penalties):
            doc = frappe.get_doc("Sales Invoice", penalty.name)
            if idx == 0:
                latest_invoice = doc
            else:
                try:
                    if doc.docstatus == 1:
                        doc.cancel()
                    elif doc.docstatus == 0:
                        frappe.delete_doc("Sales Invoice", doc.name, ignore_permissions=True)
                except Exception:
                    frappe.log_error(frappe.get_traceback(), f"Failed to cancel/delete penalty invoice {doc.name}")

        if latest_invoice:
            previous_total = sum(float(it.amount or 0) for it in latest_invoice.items)
            if previous_total == new_total:
                if latest_invoice.docstatus == 0:
                    latest_invoice.items = []  
                    for item in items:
                        latest_invoice.append("items", item)
                    latest_invoice.save(ignore_permissions=True)
                    frappe.msgprint(f"Penalty Invoice {latest_invoice.name} updated for {original_invoice.name}")
                return
            else:
                if latest_invoice.docstatus == 1:
                    latest_invoice.cancel()
                else:
                    frappe.delete_doc("Sales Invoice", latest_invoice.name, ignore_permissions=True)

        invoice = frappe.new_doc("Sales Invoice")
        invoice.customer = original_invoice.customer
        invoice.due_date = add_days(today(), 7)
        invoice.posting_date = today()

        for item in items:
            invoice.append("items", item)

        invoice.remarks = penalty_remarks
        invoice.utility_service_request = service_request
        invoice.reference_invoice = original_invoice.name
        invoice.is_penalty_invoice = 1

        invoice.insert(ignore_permissions=True)
        if rule.submit_penalty_invoice:
            invoice.submit()

        comment_content = (
            f"Penalty invoice <a href='/app/sales-invoice/{invoice.name}'>{invoice.name}</a> "
            f"was created for overdue invoice <a href='/app/sales-invoice/{original_invoice.name}'>{original_invoice.name}</a>."
        )

        add_comment("Sales Invoice", original_invoice.name, comment_content)
        if getattr(original_invoice, "utility_service_request", None):
            add_comment("Utility Service Request", original_invoice.utility_service_request, comment_content)

        frappe.msgprint(f"Penalty Invoice {invoice.name} created for {original_invoice.name}")

    except Exception:
        frappe.log_error(f"Error in create_penalty_invoice for {original_invoice.name}: {frappe.get_traceback()}")


def add_comment(doctype: str, name: str, content: str) -> None:
    try:
        frappe.get_doc({
            "doctype": "Comment",
            "comment_type": "Info",
            "reference_doctype": doctype,
            "reference_name": name,
            "content": content
        }).insert(ignore_permissions=True)
    except Exception as e:
        frappe.log_error(f"Error adding comment to {doctype} {name}: {frappe.get_traceback()}")
