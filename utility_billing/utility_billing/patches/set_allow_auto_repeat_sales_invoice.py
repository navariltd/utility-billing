import frappe

def execute():
    # Update the Sales Invoice DocType to allow auto-repeat
    invoice = frappe.get_doc("DocType", "Sales Invoice")
    
    if invoice:
        invoice.allow_auto_repeat = 1
        invoice.save()
    
    frappe.db.commit()
