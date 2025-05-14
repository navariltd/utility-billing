import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import (
    add_months,
    getdate,
    formatdate,
    today,
    flt,
)

@frappe.whitelist()
def on_update(doc: Document, method: str) -> None:
   
    if not is_status_changed_to_completed(doc):
        return

    if not should_process_increment(doc):
        return

    adjustment_rule = frappe.get_doc("Billing Adjustment Rule", doc.adjustment_rule)
    if not adjustment_rule:
        return

    if is_contract_ended(doc):
        return

    new_invoice = create_renewal_invoice(doc, adjustment_rule)
    new_invoice.save()
    if not new_invoice:
        return

    new_auto_repeat = create_auto_repeat(doc, new_invoice, adjustment_rule)
    add_audit_comment(doc, new_invoice, new_auto_repeat, adjustment_rule)

def is_status_changed_to_completed(doc: Document) -> bool:
    """Check if status changed from Active to Completed"""
    previous_doc = doc.get_doc_before_save()
    if not previous_doc:
        return False
    
    status_changed = doc.has_value_changed("status")
    current_status = doc.status

    
    return status_changed and previous_doc.status == "Active" and current_status == "Completed"

def should_process_increment(doc: Document) -> bool:
    """Check if increment should be processed"""
    if not getattr(doc, 'enable_increment', 0):
        frappe.msgprint(_("Increment not enabled for this invoice"))
        return False
    return True
def is_contract_ended(doc: Document) -> bool:
    """Check if contract has already ended"""
    contract_end_date = getattr(doc, 'contract_end_date', None)
    if contract_end_date and getdate(contract_end_date) < getdate(today()):
        frappe.msgprint(_("Contract ended on {0}. Cannot generate renewal.").format(
            formatdate(getdate(contract_end_date))
        ), alert=True)
        return True
    return False

def create_renewal_invoice(doc: Document, adjustment_rule) -> Document:
    """Create a new invoice with adjusted rates"""
    new_invoice = get_invoice_copy(doc)
    set_invoice_dates(new_invoice, adjustment_rule)
    apply_rate_adjustments(new_invoice, adjustment_rule)
    
    try:
        new_invoice.calculate_taxes_and_totals()
        new_invoice.insert(ignore_permissions=True)
        return new_invoice
    except Exception as e:
        frappe.log_error(_("Error creating renewal invoice"), e)
        frappe.throw(_("Failed to create renewal invoice: {0}").format(str(e)))
        return None

def get_invoice_copy(doc: Document) -> Document:
    """Create a copy of the linked invoice from the Auto Repeat doc"""
    if not doc.reference_document:
        frappe.throw(_("No linked invoice found in Auto Repeat"))
    original_invoice = frappe.get_doc("Sales Invoice", doc.reference_document)
    print("Original Invoice: ", original_invoice)
    return frappe.copy_doc(original_invoice)
    
    
def set_invoice_dates(invoice: Document, adjustment_rule) -> None:
    """Set posting and due dates for the invoice based on today's date and adjustment rule."""
    from frappe.utils import add_days, today, getdate

    invoice.posting_date = getdate(today())

    overdue_after_days = getattr(adjustment_rule, 'overdue_after_days', 10)

    invoice.due_date = add_days(invoice.posting_date, overdue_after_days)


def apply_rate_adjustments(invoice: Document, adjustment_rule) -> None:
    """Apply rate adjustments to all items based on the adjustment rule"""
    effective_increment = get_effective_increment(adjustment_rule)
    
    for item in invoice.items:
        original_rate = get_original_item_rate(invoice.name, item.item_code)
        item.rate = calculate_new_rate(item.rate, original_rate, effective_increment, adjustment_rule)
        item.amount = flt(item.qty) * flt(item.rate)

def get_effective_increment(adjustment_rule) -> float:
    """Get the effective increment percentage considering adjustment cap"""
    increment_percent = adjustment_rule.increment_percentage
    if getattr(adjustment_rule, 'adjustment_cap', 0) and increment_percent > adjustment_rule.adjustment_cap:
        return adjustment_rule.adjustment_cap
    return increment_percent

def calculate_new_rate(current_rate: float, original_rate: float, 
                     increment_percent: float, adjustment_rule) -> float:
    """Calculate new rate based on adjustment basis"""
    if adjustment_rule.adjustment_basis == "Original Amount" and original_rate is not None:
        return original_rate * (1 + (increment_percent / 100))
    else:
        return flt(current_rate) * (1 + (increment_percent / 100))

def get_original_item_rate(invoice_name: str, item_code: str) -> float:
    """Trace back to the original invoice to get the original rate for an item"""
    original_rate = None
    current_invoice = invoice_name
    
    while current_invoice:
        invoice = frappe.get_doc("Sales Invoice", current_invoice)
        for item in invoice.items:
            if item.item_code == item_code:
                original_rate = flt(item.rate)
        
        if invoice.auto_repeat:
            auto_repeat = frappe.get_doc("Auto Repeat", invoice.auto_repeat)
            if auto_repeat.reference_document != current_invoice:
                current_invoice = auto_repeat.reference_document
            else:
                current_invoice = None
        else:
            current_invoice = None
    
    return original_rate

def create_auto_repeat(doc: Document, new_invoice: Document, adjustment_rule) -> Document:
    """Create new Auto Repeat record for the renewal"""
    new_auto_repeat = frappe.get_doc({
        "doctype": "Auto Repeat",
        "reference_doctype": "Sales Invoice",
        "reference_document": new_invoice.name,
        "frequency": adjustment_rule.frequency,
        "submit_on_creation": adjustment_rule.submit_on_creation,
        "repeat_on_day": adjustment_rule.repeat_on_day,
        "repeat_on_last_day": adjustment_rule.repeat_on_last_day,
        "start_date": new_invoice.posting_date,
        "end_date": get_auto_repeat_end_date(doc, new_invoice.posting_date, adjustment_rule),
        "contract_start_date": getattr(doc, 'contract_start_date', None),
        "contract_end_date": getattr(doc, 'contract_end_date', None),
        "enable_increment": 1,
        "notify_by_email": 0,
        "adjustment_rule": adjustment_rule.name,
        "utility_property": getattr(doc, 'utility_property', None)
    })
    new_auto_repeat.insert(ignore_permissions=True)
    return new_auto_repeat

def get_auto_repeat_end_date(doc: Document, start_date, adjustment_rule):
    """Calculate end date for auto repeat considering contract end date"""
    contract_end_date = getattr(doc, 'contract_end_date', None)
    if not contract_end_date:
        return None

    start_date_obj = getdate(start_date)
    contract_end_date_obj = getdate(contract_end_date)
    proposed_end_date = add_months(start_date_obj, adjustment_rule.increment_interval_months) \
        if adjustment_rule.increment_interval_months else None

    if proposed_end_date and proposed_end_date > contract_end_date_obj:
        return contract_end_date_obj
    return proposed_end_date


def add_audit_comment(doc: Document, new_invoice: Document, 
                        auto_repeat: Document, adjustment_rule) -> None:
    """Add audit comment documenting the renewal to multiple related documents"""
    comment_msg = _("""
        <div class='small'>
            <b>Bill Increment Renewal Generated:</b><br>
            • Original Invoice: <a href='/app/sales-invoice/{or_inv}'>{or_inv}</a><br>
            • New Invoice: <a href='/app/sales-invoice/{new_inv}'>{new_inv}</a><br>
            • Period: {start} to {end}<br>
            • Rate Increase: {inc}%<br>
            • Adjustment Rule: <a href='/app/billing-adjustment-rule/{rule}'>{rule}</a><br>
            • Old Auto Repeat: {old_ar_link}<br>
            • New Auto Repeat: <a href='/app/auto-repeat/{ar}'>{ar}</a>
        </div>
    """).format(
        or_inv=doc.reference_document,
        new_inv=new_invoice.name,
        start=formatdate(new_invoice.posting_date),
        end=formatdate(auto_repeat.end_date) if auto_repeat.end_date else _("No end date"),
        inc=get_effective_increment(adjustment_rule),
        rule=adjustment_rule.name,
        old_ar_link=("<a href='/app/auto-repeat/{0}'>{0}</a>".format(doc.name) if doc else _("N/A")),
        ar=auto_repeat.name
    )

    # List of (doctype, name) pairs to add the comment to
    targets = [
        ("Sales Invoice", doc.reference_document),
        ("Sales Invoice", new_invoice.name),
        ("Auto Repeat", doc.name) if doc else None,
        ("Auto Repeat", auto_repeat.name),
    ]

    utility_service_request = getattr(new_invoice, "utility_service_request", None)
    if utility_service_request:
        targets.append(("Utility Service Request", utility_service_request))

    for doctype, name in filter(None, targets):
        frappe.get_doc({
            "doctype": "Comment",
            "comment_type": "Info",
            "reference_doctype": doctype,
            "reference_name": name,
            "content": comment_msg
        }).insert(ignore_permissions=True)
