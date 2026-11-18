import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, add_days


class UtilityBillStructureAssignment(Document):
    def validate(self):
        if self.end_date and getdate(self.end_date) < getdate(self.start_date):
            frappe.throw(_('End Date must be on or after Start Date.'))
        # Serialize date changes and replacement submissions for this customer.
        frappe.db.get_value('Customer', self.customer, 'name', for_update=True)
        structure = frappe.get_doc('Utility Bill Structure', self.utility_bill_structure)
        if structure.docstatus != 1:
            frappe.throw(_('Select a submitted Bill Structure.'))
        if structure.company != self.company:
            frappe.throw(_('Assignment and Bill Structure must have the same company.'))
        if self.property and frappe.db.get_value('Utility Property', self.property, 'company') != self.company:
            frappe.throw(_('Property must belong to the assignment company.'))
        replacing = self.docstatus == 0 or getattr(self, '_action', None) == 'submit'
        others = frappe.get_all(self.doctype, filters={
            'customer': self.customer, 'company': self.company, 'docstatus': 1,
            'name': ('!=', self.name or ''),
        }, fields=['name', 'property', 'start_date', 'end_date'])
        overlaps = [other for other in others
            if (other.property or '') == (self.property or '')
            and getdate(other.start_date) <= getdate(self.end_date or '9999-12-31')
            and getdate(self.start_date) <= getdate(other.end_date or '9999-12-31')]
        if overlaps:
            candidate = overlaps[0]
            can_replace = (replacing and len(overlaps) == 1
                and getdate(candidate.start_date) < getdate(self.start_date)
                and (not candidate.end_date or self.get('previous_assignment') == candidate.name)
                and (not self.get('previous_assignment') or self.previous_assignment == candidate.name))
            if not can_replace:
                frappe.throw(_('An assignment already covers this customer and property during this period.'))
            self.previous_assignment = candidate.name
        if self.get('previous_assignment'):
            previous = frappe.get_doc(self.doctype, self.previous_assignment)
            if previous.docstatus != 1 or any((previous.get(k) or '') != (self.get(k) or '') for k in ('customer', 'company', 'property')):
                frappe.throw(_('Previous Assignment must belong to this customer, company and property.'))
            if getdate(self.start_date) <= getdate(previous.start_date):
                frappe.throw(_('The new assignment must start after the previous assignment starts.'))
            pending_close = replacing and (not previous.end_date or getdate(previous.end_date) >= getdate(self.start_date))
            if not pending_close and (not previous.end_date or getdate(add_days(previous.end_date, 1)) != getdate(self.start_date)):
                frappe.throw(_('The new assignment must start the day after the previous assignment ends.'))

    def before_submit(self):
        # Drafts never end a customer's current assignment or change its schedule.
        self.validate()
        if not self.get('previous_assignment'):
            return
        previous = frappe.get_doc(self.doctype, self.previous_assignment)
        if previous.end_date and getdate(previous.end_date) < getdate(self.start_date):
            return
        previous.check_permission('write')
        schedule = frappe.get_doc('Auto Repeat', previous.billing_auto_repeat) if previous.get('billing_auto_repeat') else None
        if schedule and getdate(self.start_date).day != 1:
            frappe.throw(_('For recurring fixed billing, change structures on the first day of a month.'))
        if schedule and not schedule.disabled and schedule.status == 'Active':
            self.flags.replacement_reference_doctype = schedule.reference_doctype
        previous.end_date = add_days(self.start_date, -1)
        previous.save()  # Includes bill-date protection and schedule-end synchronization.

    def on_submit(self):
        reference_doctype = self.flags.get('replacement_reference_doctype')
        if reference_doctype and not frappe.get_doc('Utility Bill Structure', self.utility_bill_structure).metered_billing:
            from ...utils.fixed_billing import start_billing
            start_billing(self, self.start_date, reference_doctype)

    def on_update_after_submit(self):
        self.validate()
        latest = frappe.db.get_value('Meter Reading', {'bill_structure_assignment': self.name, 'docstatus': 1}, 'date', order_by='date desc')
        if latest and self.end_date and getdate(latest) > getdate(self.end_date):
            frappe.throw(_('End Date cannot exclude an already submitted bill.'))
        from ...utils.fixed_billing import validate_assignment_end, sync_schedule_end
        validate_assignment_end(self)
        sync_schedule_end(self)

    @frappe.whitelist()
    def start_billing(self, billing_date=None, reference_doctype='Sales Invoice'):
        from ...utils.fixed_billing import start_billing
        return start_billing(self, billing_date, reference_doctype)

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
        savepoint = 'change_bill_structure_' + frappe.generate_hash(length=8)
        frappe.db.savepoint(savepoint)
        try:
            replacement = frappe.get_doc(dict(doctype=self.doctype, customer=self.customer, company=self.company,
                property=self.property, utility_bill_structure=new_structure, start_date=effective_date,
                end_date=self.end_date if self.end_date and getdate(self.end_date) >= effective_date else None,
                previous_assignment=self.name))
            replacement.insert()
            replacement.submit()
            return replacement.name
        except Exception:
            frappe.db.rollback(save_point=savepoint)
            raise
