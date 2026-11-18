"""Open-ended assignment transitions, using temporary records and no ERPNext fixtures."""
import frappe
from frappe.utils import add_days, add_months, get_first_day, getdate, nowdate


def run_site_checks():
    if frappe.local.site != 'utility-billing.localhost':
        frappe.throw('Site checks are restricted to utility-billing.localhost.')
    from utility_billing.utility_billing.utils.structure_billing import assignment_for_date
    try:
        customer = frappe.get_doc(dict(doctype='Customer', customer_name='Assignment verification ' + frappe.generate_hash(length=6),
            customer_type='Individual', customer_group='Individual', territory='Kenya', default_price_list='Water Tariffs')).insert()
        company = 'Mwangaza Water Services'
        old = frappe.get_doc(dict(doctype='Utility Bill Structure Assignment', customer=customer.name, company=company,
            utility_bill_structure='Residential Water Only', start_date=get_first_day(nowdate()))).insert()
        old.submit()
        effective = get_first_day(add_months(nowdate(), 1))
        replacement = frappe.get_doc(dict(doctype=old.doctype, customer=customer.name, company=company,
            utility_bill_structure='Residential Water and Sewerage', start_date=effective)).insert()
        old.reload()
        assert old.end_date is None, 'Saving a draft must not end the current assignment'
        assert replacement.previous_assignment == old.name
        replacement.submit()
        old.reload()
        assert getdate(old.end_date) == getdate(add_days(effective, -1))
        assert replacement.end_date is None
        assert assignment_for_date(customer.name, company, old.end_date)['name'] == old.name
        assert assignment_for_date(customer.name, company, effective)['name'] == replacement.name
        # Equal start dates must still be rejected, rather than replacing the existing record.
        try:
            frappe.get_doc(dict(doctype=old.doctype, customer=customer.name, company=company,
                utility_bill_structure='Residential Water Only', start_date=effective)).insert()
        except frappe.ValidationError:
            pass
        else:
            raise AssertionError('Duplicate assignment start date was accepted')
        # The dedicated Change Bill Structure action follows the same open-ended transition.
        later = get_first_day(add_months(effective, 1))
        next_name = replacement.change_structure('Residential Water Only', later)
        replacement.reload()
        assert getdate(replacement.end_date) == getdate(add_days(later, -1))
        assert frappe.get_doc(old.doctype, next_name).previous_assignment == replacement.name
        return dict(draft_preserves_current=True, open_end_closed_on_submit=True, historical_dates_correct=True,
                    duplicate_start_blocked=True, change_structure_action=True, rolled_back=True)
    finally:
        frappe.db.rollback()
