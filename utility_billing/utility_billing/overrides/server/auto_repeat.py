import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import (
    add_days,
    add_months,
    getdate,
    formatdate,
    today,
    flt,
)
from typing import Optional, Dict, Any

@frappe.whitelist()
def on_update(doc: Document, method: str) -> None:
    """Main handler for Auto Repeat document updates"""
    auto_repeat_doc = doc
    if not is_status_changed_to_completed(auto_repeat_doc):
        return

    if not should_process_increment(auto_repeat_doc):
        return

    adjustment_rule = frappe.get_doc("Billing Adjustment Rule", auto_repeat_doc.adjustment_rule)
    if not adjustment_rule:
        return

    if is_contract_ended(auto_repeat_doc):
        return

    new_reference_doc = create_renewal_document(auto_repeat_doc, adjustment_rule)
    if not new_reference_doc:
        return

    new_auto_repeat = create_auto_repeat(auto_repeat_doc, new_reference_doc, adjustment_rule)
    new_auto_repeat.start_date = add_days(auto_repeat_doc.end_date, 1)
    new_auto_repeat.save(ignore_permissions=True)
    add_audit_comment(auto_repeat_doc, new_reference_doc, new_auto_repeat, adjustment_rule)

def is_status_changed_to_completed(auto_repeat_doc: Document) -> bool:
    """Check if status changed from Active to Completed"""
    previous_doc = auto_repeat_doc.get_doc_before_save()
    if not previous_doc:
        return False
    
    status_changed = auto_repeat_doc.has_value_changed("status")
    current_status = auto_repeat_doc.status
    
    return status_changed and previous_doc.status == "Active" and current_status == "Completed"

def should_process_increment(auto_repeat_doc: Document) -> bool:
    """Check if increment should be processed"""
    if not getattr(auto_repeat_doc, 'enable_increment', 0):
        frappe.msgprint(_("Increment not enabled for this Auto Repeat"))
        return False
    return True

def is_contract_ended(auto_repeat_doc: Document) -> bool:
    """Check if contract has already ended"""
    contract_end_date = getattr(auto_repeat_doc, 'contract_end_date', None)
    if contract_end_date and getdate(contract_end_date) < getdate(today()):
        frappe.msgprint(_("Contract ended on {0}. Cannot generate renewal.").format(
            formatdate(getdate(contract_end_date))
        ), alert=True)
        return True
    return False

def create_renewal_document(auto_repeat_doc: Document, adjustment_rule: Document) -> Optional[Document]:
    """Create a new reference document with adjusted rates"""
    new_reference_doc = get_document_copy(auto_repeat_doc)
    set_document_dates(new_reference_doc, adjustment_rule, auto_repeat_doc.end_date)
    apply_rate_adjustments(auto_repeat_doc, new_reference_doc, adjustment_rule)
    
    try:
        if hasattr(new_reference_doc, 'calculate_taxes_and_totals'):
            new_reference_doc.calculate_taxes_and_totals()
        new_reference_doc.insert(ignore_permissions=True)
        return new_reference_doc
    except Exception as e:
        frappe.log_error(_("Error creating renewal document"), e)
        frappe.throw(_("Failed to create renewal document: {0}").format(str(e)))
        return None

def get_document_copy(auto_repeat_doc: Document) -> Document:
    """Create a copy of the linked reference document from the Auto Repeat doc"""
    if not auto_repeat_doc.reference_document:
        frappe.throw(_("No linked document found in Auto Repeat"))
    
    return frappe.copy_doc(frappe.get_doc(
        auto_repeat_doc.reference_doctype, 
        auto_repeat_doc.reference_document
    ))

def set_document_dates(reference_doc: Document, adjustment_rule: Document, date: str) -> None:
    """Set posting and due dates for the reference document"""
    if hasattr(reference_doc, 'posting_date'):
        reference_doc.posting_date = getdate(date)

    if hasattr(reference_doc, 'due_date'):
        overdue_after_days = getattr(adjustment_rule, 'overdue_after_days', 10)
        reference_doc.due_date = add_days(reference_doc.posting_date, overdue_after_days)

def apply_rate_adjustments(
    auto_repeat_doc: Document, 
    reference_doc: Document, 
    adjustment_rule: Document
) -> None:
    """Apply rate adjustments to all items in the reference document"""
    effective_increment = get_effective_increment(adjustment_rule)
    
    if hasattr(reference_doc, 'items'):
        for item in reference_doc.items:
            if not hasattr(item, 'rate'):
                continue
                
            original_rate = get_original_item_rate(
                auto_repeat_doc.reference_doctype, 
                auto_repeat_doc.reference_document, 
                item.item_code
            )
            item.rate = calculate_new_rate(
                item.rate, 
                original_rate, 
                effective_increment, 
                adjustment_rule
            )
            if hasattr(item, 'amount') and hasattr(item, 'qty'):
                item.amount = flt(item.qty) * flt(item.rate)

def get_effective_increment(adjustment_rule: Document) -> float:
    """Get the effective increment percentage considering adjustment cap"""
    increment_percent = flt(adjustment_rule.increment_percentage)
    if getattr(adjustment_rule, 'adjustment_cap', 0) and increment_percent > adjustment_rule.adjustment_cap:
        return flt(adjustment_rule.adjustment_cap)
    return increment_percent

def calculate_new_rate(
    current_rate: float, 
    original_rate: Optional[float], 
    increment_percent: float, 
    adjustment_rule: Document
) -> float:
    """Calculate new rate based on adjustment basis"""
    if adjustment_rule.adjustment_basis == "Original Amount" and original_rate is not None:
        return original_rate * (1 + (increment_percent / 100))
    return flt(current_rate) * (1 + (increment_percent / 100))

def get_original_item_rate(
    doctype: str, 
    docname: str, 
    item_code: str
) -> Optional[float]:
    """Trace back to the original document to get the original rate for an item"""
    original_rate = None
    current_doc = docname
    
    while current_doc:
        doc = frappe.get_doc(doctype, current_doc)
        if hasattr(doc, 'items'):
            for item in doc.items:
                if item.item_code == item_code and hasattr(item, 'rate'):
                    original_rate = flt(item.rate)
                    break
        
        if hasattr(doc, 'auto_repeat') and doc.auto_repeat:
            auto_repeat = frappe.get_doc("Auto Repeat", doc.auto_repeat)
            if auto_repeat.reference_document != current_doc:
                current_doc = auto_repeat.reference_document
            else:
                current_doc = None
        else:
            current_doc = None
    
    return original_rate

def create_auto_repeat(
    original_auto_repeat: Document, 
    new_reference_doc: Document, 
    adjustment_rule: Document
) -> Document:
    """Create new Auto Repeat record for the renewal"""
    new_auto_repeat = frappe.get_doc({
        "doctype": "Auto Repeat",
        "reference_doctype": new_reference_doc.doctype,
        "reference_document": new_reference_doc.name,
        "frequency": adjustment_rule.frequency,
        "submit_on_creation": adjustment_rule.submit_on_creation,
        "repeat_on_day": adjustment_rule.repeat_on_day,
        "repeat_on_last_day": adjustment_rule.repeat_on_last_day,
        "start_date": original_auto_repeat.end_date,
        "end_date": get_auto_repeat_end_date(
            original_auto_repeat, 
            original_auto_repeat.end_date, 
            adjustment_rule
        ),
        "contract_start_date": getattr(original_auto_repeat, 'contract_start_date', None),
        "contract_end_date": getattr(original_auto_repeat, 'contract_end_date', None),
        "enable_increment": 1,
        "notify_by_email": 0,
        "adjustment_rule": adjustment_rule.name,
        "utility_property": getattr(original_auto_repeat, 'utility_property', None)
    })
    new_auto_repeat.insert(ignore_permissions=True)
    return new_auto_repeat

def get_auto_repeat_end_date(
    auto_repeat_doc: Document, 
    start_date: str, 
    adjustment_rule: Document
) -> Optional[str]:
    """Calculate end date for auto repeat considering contract end date"""
    contract_end_date = getattr(auto_repeat_doc, 'contract_end_date', None)
    if not contract_end_date:
        return None

    start_date_obj = getdate(start_date)
    contract_end_date_obj = getdate(contract_end_date)
    proposed_end_date = add_months(start_date_obj, flt(adjustment_rule.increment_interval_months)) \
        if adjustment_rule.increment_interval_months else None

    if proposed_end_date and proposed_end_date > contract_end_date_obj:
        return contract_end_date_obj
    return proposed_end_date if proposed_end_date else None

def add_audit_comment(
    original_auto_repeat: Document, 
    new_reference_doc: Document, 
    new_auto_repeat: Document, 
    adjustment_rule: Document
) -> None:
    """Add audit comment documenting the renewal to multiple related documents"""
    comment_msg = _("""
        <div class='small'>
            <b>Billing Increment Renewal Generated:</b><br>
            • Original Document: <a href='/app/{or_doctype}/{or_doc}'>{or_doc}</a><br>
            • New Document: <a href='/app/{new_doctype}/{new_doc}'>{new_doc}</a><br>
            • Period: {start} to {end}<br>
            • Rate Increase: {inc}%<br>
            • Adjustment Rule: <a href='/app/billing-adjustment-rule/{rule}'>{rule}</a><br>
            • Old Auto Repeat: {old_ar_link}<br>
            • New Auto Repeat: <a href='/app/auto-repeat/{ar}'>{ar}</a>
        </div>
    """).format(
        or_doctype=original_auto_repeat.reference_doctype.lower().replace(' ', '-'),
        or_doc=original_auto_repeat.reference_document,
        new_doctype=new_reference_doc.doctype.lower().replace(' ', '-'),
        new_doc=new_reference_doc.name,
        start=formatdate(original_auto_repeat.end_date) if hasattr(original_auto_repeat, 'end_date') else _("N/A"),
        end=formatdate(new_auto_repeat.end_date) if new_auto_repeat.end_date else _("No end date"),
        inc=get_effective_increment(adjustment_rule),
        rule=adjustment_rule.name,
        old_ar_link=("<a href='/app/auto-repeat/{0}'>{0}</a>".format(original_auto_repeat.name) if original_auto_repeat else _("N/A")),
        ar=new_auto_repeat.name
    )

    # List of (doctype, name) pairs to add the comment to
    targets = [
        (original_auto_repeat.reference_doctype, original_auto_repeat.reference_document),
        (new_reference_doc.doctype, new_reference_doc.name),
        ("Auto Repeat", original_auto_repeat.name) if original_auto_repeat else None,
        ("Auto Repeat", new_auto_repeat.name),
    ]

    if hasattr(new_reference_doc, 'utility_service_request') and new_reference_doc.utility_service_request:
        targets.append(("Utility Service Request", new_reference_doc.utility_service_request))

    for doctype, name in filter(None, targets):
        frappe.get_doc({
            "doctype": "Comment",
            "comment_type": "Info",
            "reference_doctype": doctype,
            "reference_name": name,
            "content": comment_msg
        }).insert(ignore_permissions=True)