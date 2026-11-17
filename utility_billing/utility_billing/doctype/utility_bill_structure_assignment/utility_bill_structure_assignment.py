import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, add_days


class UtilityBillStructureAssignment(Document):
    def validate(self):
        if self.end_date and getdate(self.end_date) < getdate(self.start_date):
            frappe.throw(_('End Date must be on or after Start Date.'))
        if self.get('previous_assignment'):
            previous = frappe.get_doc(self.doctype, self.previous_assignment)
            if previous.docstatus != 1 or any((previous.get(k) or '') != (self.get(k) or '') for k in ('customer', 'company', 'property')):
                frappe.throw(_('Previous Assignment must belong to this customer, company and property.'))
            if not previous.end_date or getdate(add_days(previous.end_date, 1)) != getdate(self.start_date):
                frappe.throw(_('The new assignment must start the day after the previous assignment ends.'))
        structure = frappe.get_doc('Utility Bill Structure', self.utility_bill_structure)
        if structure.docstatus != 1:
            frappe.throw(_('Select a submitted Bill Structure.'))
        if structure.company != self.company:
            frappe.throw(_('Assignment and Bill Structure must have the same company.'))
        if self.property and frappe.db.get_value('Utility Property', self.property, 'company') != self.company:
            frappe.throw(_('Property must belong to the assignment company.'))
        frappe.db.get_value('Customer', self.customer, 'name', for_update=True)
        for other in frappe.get_all(self.doctype, filters={
            'customer': self.customer, 'company': self.company, 'docstatus': 1,
            'name': ('!=', self.name or ''),
        }, fields=['property', 'start_date', 'end_date']):
            if (other.property or '') == (self.property or '') and getdate(other.start_date) <= getdate(self.end_date or '9999-12-31') and getdate(self.start_date) <= getdate(other.end_date or '9999-12-31'):
                frappe.throw(_('An assignment already covers this customer and property during this period.'))


    def on_update_after_submit(self):
        self.validate()
        latest = frappe.db.get_value('Meter Reading', {'bill_structure_assignment': self.name, 'docstatus': 1}, 'date', order_by='date desc')
        if latest and self.end_date and getdate(latest) > getdate(self.end_date):
            frappe.throw(_('End Date cannot exclude an already submitted bill.'))

    @frappe.whitelist()
    def change_structure(self, new_structure, effective_date):
        self.check_permission('write')
        if self.docstatus != 1:
            frappe.throw(_('Submit the current assignment first.'))
        effective_date = getdate(effective_date)
        if effective_date <= getdate(self.start_date):
            frappe.throw(_('The new assignment must start after the current assignment starts.'))
        if self.end_date and effective_date > getdate(add_days(self.end_date, 1)):
            frappe.throw(_('The new assignment must start within or immediately after the current assignment period.'))
        if new_structure == self.utility_bill_structure:
            frappe.throw(_('Choose a different Bill Structure.'))
        original_end = self.end_date
        self.end_date = add_days(effective_date, -1)
        self.save()
        replacement = frappe.get_doc(dict(doctype=self.doctype, customer=self.customer, company=self.company,
            property=self.property, utility_bill_structure=new_structure, start_date=effective_date,
            end_date=original_end if original_end and getdate(original_end) >= effective_date else None, previous_assignment=self.name))
        replacement.insert()
        replacement.submit()
        return replacement.name
