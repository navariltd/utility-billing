"""Focused fixed-billing checks; no ERPNext test fixtures are loaded."""
from unittest import TestCase
from unittest.mock import patch

import frappe
from frappe.utils import add_days, add_months, get_first_day, getdate, nowdate

from utility_billing.utility_billing.utils.fixed_billing import fixed_structure


class TestFixedBilling(TestCase):
    def test_metered_structures_are_refused(self):
        assignment = frappe._dict(docstatus=1, start_date='2026-01-01', end_date=None, utility_bill_structure='Water')
        with patch('frappe.get_doc', return_value=frappe._dict(docstatus=1, metered_billing=1)):
            with self.assertRaises(frappe.ValidationError):
                fixed_structure(assignment, '2026-11-18')

    def test_assignment_dates_are_enforced(self):
        assignment = frappe._dict(docstatus=1, start_date='2026-11-01', end_date='2026-11-30')
        for date in ('2026-10-31', '2026-12-01'):
            with self.assertRaises(frappe.ValidationError):
                fixed_structure(assignment, date)


def run_site_checks():
    """Use existing sample records in one rolled-back transaction."""
    if frappe.local.site != 'utility-billing.localhost':
        frappe.throw('Site checks are restricted to utility-billing.localhost.')
    from utility_billing.utility_billing.utils.fixed_billing import create_bill, start_billing
    try:
        sample_name = frappe.db.get_value('Utility Bill Structure Assignment',
            {'customer': 'Peter Kamau', 'docstatus': 1}, 'name')
        sample = frappe.get_doc('Utility Bill Structure Assignment', sample_name)
        date = nowdate()
        customer = frappe.get_doc(dict(doctype='Customer', customer_name='Billing verification ' + frappe.generate_hash(length=6),
            customer_type='Individual', customer_group='Individual', territory='Kenya', default_price_list='Water Tariffs')).insert()
        assignment = frappe.get_doc(dict(doctype='Utility Bill Structure Assignment', customer=customer.name, company=sample.company,
            utility_bill_structure=sample.utility_bill_structure, start_date=get_first_day(date))).insert()
        assignment.submit()
        assignment_name = assignment.name
        frappe.db.savepoint('fixed_billing_setup')
        result = start_billing(assignment, date)
        invoice = frappe.get_doc(result['doctype'], result['name'])
        assert invoice.doctype == 'Sales Invoice'
        assert invoice.docstatus == 0
        assert invoice.net_total == 700, invoice.net_total
        assert [(r.qty, r.rate) for r in invoice.items] == [(1, 500), (1, 200)]
        assert not invoice.update_stock
        assert not invoice.get('meter_readings')
        from utility_billing.utility_billing.utils.structure_billing import check_monthly_duplicate
        legacy_reading = frappe.get_doc(dict(doctype='Meter Reading', customer=customer.name, company=assignment.company,
            date=date, bill_structure_assignment=assignment.name))
        try:
            check_monthly_duplicate(legacy_reading)
        except frappe.ValidationError:
            pass
        else:
            raise AssertionError('A legacy Meter Reading could duplicate the fixed bill')
        assignment.reload()
        assert start_billing(assignment, date)['name'] == invoice.name
        repeat = frappe.get_doc('Auto Repeat', result['auto_repeat'])
        assert repeat.frequency == 'Monthly'
        assert not repeat.submit_on_creation
        assert getdate(repeat.next_schedule_date) == getdate(add_months(date, 1))
        next_date = add_months(date, 1)
        repeat.next_schedule_date = next_date
        next_invoice = repeat.make_new_document()
        assert next_invoice.net_total == 700
        assert getdate(next_invoice.utility_billing_date) == getdate(next_date)
        assert repeat.make_new_document().name == next_invoice.name
        duplicate = frappe.copy_doc(next_invoice)
        try:
            duplicate.insert()
        except frappe.ValidationError:
            pass
        else:
            raise AssertionError('Duplicate monthly invoice was accepted')
        # A non-metered formula must be recalculated for each month's day count.
        fy = frappe.db.get_value('Fiscal Year', {'year_start_date': ('<=', date), 'year_end_date': ('>=', date)}, 'name')
        label = 'Monthly Service ' + frappe.generate_hash(length=6)
        structure = frappe.get_doc(dict(doctype='Utility Bill Structure', naming_series='UBS-.YYYY.-', fiscal_year=fy,
            company=assignment.company, items=[dict(item='Service Charge', calculation_type='Formula', formula='days_in_month * 10')])).insert()
        structure.submit()
        # The December draft above must block a change that would invalidate it.
        effective = get_first_day(next_date)
        try:
            assignment.change_structure(structure.name, effective)
        except frappe.ValidationError:
            pass
        else:
            raise AssertionError('An existing December bill was invalidated')
        # Undo the intentionally rejected operations before testing a clean transition.
        frappe.db.rollback(save_point='fixed_billing_setup')
        assignment = frappe.get_doc('Utility Bill Structure Assignment', assignment_name)
        result = start_billing(assignment, date)
        structure = frappe.get_doc(dict(doctype='Utility Bill Structure', naming_series='UBS-.YYYY.-', fiscal_year=fy,
            company=assignment.company, items=[dict(item='Service Charge', calculation_type='Formula', formula='days_in_month * 10')])).insert()
        structure.submit()
        replacement_name = assignment.change_structure(structure.name, effective)
        replacement = frappe.get_doc('Utility Bill Structure Assignment', replacement_name)
        old_repeat = frappe.get_doc('Auto Repeat', result['auto_repeat'])
        assert old_repeat.disabled
        assert replacement.previous_assignment == assignment.name
        assert replacement.billing_auto_repeat
        new_repeat = frappe.get_doc('Auto Repeat', replacement.billing_auto_repeat)
        changed_invoice = frappe.get_doc('Sales Invoice', new_repeat.reference_document)
        assert changed_invoice.net_total == 310
        if not frappe.db.exists('Fiscal Year', '2027'):
            frappe.get_doc(dict(doctype='Fiscal Year', year='2027', year_start_date='2027-01-01', year_end_date='2027-12-31')).insert()
        new_repeat.next_schedule_date = '2027-02-01'
        february_invoice = new_repeat.make_new_document()
        assert february_invoice.net_total == 280
        assert february_invoice.bill_structure_assignment == replacement.name
        frappe.db.rollback(save_point='fixed_billing_setup')
        assignment = frappe.get_doc('Utility Bill Structure Assignment', assignment_name)
        order_result = start_billing(assignment, date, 'Sales Order')
        order = frappe.get_doc('Sales Order', order_result['name'])
        assert order.net_total == 700
        order.submit()
        from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice
        mapped = make_sales_invoice(order.name)
        mapped.insert()
        assert mapped.net_total == 700
        assert mapped.bill_structure_assignment == assignment_name
        assert all(row.sales_order == order.name for row in mapped.items)
        order.save()
        return dict(order_to_invoice=True, first_total=700, duplicate_blocked=True, transition_total=310, february_total=280, rolled_back=True)
    finally:
        frappe.db.rollback()


def run_checks():
    import unittest
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(TestFixedBilling))
    if not result.wasSuccessful():
        raise AssertionError('Fixed billing checks failed')
    return dict(tests=result.testsRun, passed=True)
