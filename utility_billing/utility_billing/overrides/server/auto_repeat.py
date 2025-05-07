import frappe
from frappe import _
from frappe.model.document import Document


@frappe.whitelist()
def on_update(doc: Document, method: str) -> None:
    previous_doc = doc.get_doc_before_save()
    status_changed = doc.has_value_changed("status")
    current_status = doc.status
    
    if status_changed and previous_doc.status == "Active" and current_status == "Completed":
        if getattr(doc, 'enable_increment', 0):
            from frappe.utils import add_months, getdate, add_days, formatdate, today
            
            settings = frappe.get_doc("Utility Billing Settings", "Utility Billing Settings")
            grace_period = settings.grace_period or 10
            
            # Check if contract has already ended
            contract_end_date = getattr(doc, 'contract_end_date', None)
            if contract_end_date and getdate(contract_end_date) < getdate(today()):
                frappe.msgprint(_("Contract ended on {0}. Cannot generate renewal.").format(
                    formatdate(contract_end_date)
                ), alert=True)
                return
            
            increment_months = getattr(doc, 'increment_interval_months', 0) or 0
            increment_percent = getattr(doc, 'increment_percentage', 0) or 0
            
            # Calculate new dates with contract end date validation
            new_start_date = add_months(getdate(doc.end_date), 1)
            
            # Ensure new period doesn't exceed contract end date
            if contract_end_date:
                proposed_end_date = add_months(new_start_date, increment_months) if increment_months else None
                if proposed_end_date and proposed_end_date > getdate(contract_end_date):
                    new_end_date = contract_end_date
                else:
                    new_end_date = proposed_end_date
            else:
                new_end_date = add_months(new_start_date, increment_months) if increment_months else None
            
            # Create new invoice copy
            new_invoice = frappe.copy_doc(doc)
            new_invoice.name = None
            new_invoice.creation = None
            new_invoice.modified = None
            new_invoice.docstatus = 0
            new_invoice.posting_date = new_start_date
            new_invoice.due_date = add_days(new_start_date, grace_period)
            
            # Apply rate increment
            for item in new_invoice.items:
                item.rate = float(item.rate) * (1 + (increment_percent / 100))
                item.amount = float(item.qty) * float(item.rate)
            
            new_invoice.calculate_taxes_and_totals()
            new_invoice.insert(ignore_permissions=True)
            
            # Create new auto-repeat
            new_auto_repeat = frappe.get_doc({
                "doctype": "Auto Repeat",
                "reference_doctype": "Sales Invoice",
                "reference_document": new_invoice.name,
                **{field: getattr(doc, field) for field in [
                    'frequency', 'submit_on_creation', 'repeat_on_day',
                    'repeat_on_last_day', 'utility_property'
                ] if hasattr(doc, field)},
                "start_date": new_start_date,
                "end_date": new_end_date,
                "next_schedule_date": new_start_date,
                "contract_start_date": new_start_date,
                "contract_end_date": contract_end_date,
                "increment_interval_months": increment_months,
                "increment_percentage": increment_percent,
                "enable_increment": 1,
                "notify_by_email": 0
            })
            new_auto_repeat.insert(ignore_permissions=True)
            
            frappe.db.set_value("Sales Invoice", new_invoice.name, "auto_repeat", new_auto_repeat.name)
            
            # Add audit comment
            comment_msg = _("""
                <div class='small'>
                    <b>Renewal Generated:</b><br>
                    • Invoice: <a href='/app/sales-invoice/{new_inv}'>{new_inv}</a><br>
                    • Period: {start} to {end}<br>
                    • Rate Increase: {inc}%<br>
                    • Auto Repeat: <a href='/app/auto-repeat/{ar}'>{ar}</a>
                </div>
            """).format(
                new_inv=new_invoice.name,
                start=formatdate(new_start_date),
                end=formatdate(new_end_date) if new_end_date else _("No end date"),
                inc=increment_percent,
                ar=new_auto_repeat.name
            ) 
            
            frappe.get_doc({
                "doctype": "Comment",
                "comment_type": "Info",
                "reference_doctype": "Sales Invoice",
                "reference_name": doc.name,
                "content": comment_msg
            }).insert(ignore_permissions=True)
            
            frappe.msgprint(_("Successfully generated renewal with {0}% increase").format(increment_percent))