"""Fixed monthly bills generated from effective assignments, scheduled by Auto Repeat."""
import frappe
from frappe import _
from frappe.utils import add_days, flt, get_first_day, get_last_day, getdate, today

from .billing_formula import calculate_rows
from .structure_billing import assignment_for_date

DATE_FIELDS = {'Sales Invoice': 'posting_date', 'Sales Order': 'transaction_date'}


def fixed_structure(assignment, date):
    if assignment.docstatus != 1:
        frappe.throw(_('Submit the Bill Structure Assignment first.'))
    date = getdate(date)
    if date < getdate(assignment.start_date) or (assignment.end_date and date > getdate(assignment.end_date)):
        frappe.throw(_('The billing date must be within the assignment period.'))
    structure = frappe.get_doc('Utility Bill Structure', assignment.utility_bill_structure)
    if structure.docstatus != 1 or structure.metered_billing:
        frappe.throw(_('Start Billing requires a submitted, non-metered Bill Structure.'))
    if (structure.start_date and date < getdate(structure.start_date)) or (structure.end_date and date > getdate(structure.end_date)):
        frappe.throw(_('The billing date must be within the Bill Structure period.'))
    return structure


def scope_lock(assignment):
    frappe.db.get_value('Customer', assignment.customer, 'name', for_update=True)


def existing_bills(assignment, date, exclude=None, linked_order=None, check_meter_readings=True):
    """Reserve the month across assignments and document types, including draft bills."""
    first, last = get_first_day(date), get_last_day(date)
    assignments = frappe.get_all('Utility Bill Structure Assignment', filters={
        'customer': assignment.customer, 'company': assignment.company, 'docstatus': ('<', 2)},
        fields=['name', 'property'])
    names = [r.name for r in assignments if (r.property or '') == (assignment.property or '')]
    found = []
    for dt in DATE_FIELDS:
        filters = {'bill_structure_assignment': ('in', names), 'fixed_utility_bill': 1,
            'docstatus': ('<', 2), 'utility_billing_date': ('between', [first, last])}
        if dt == 'Sales Invoice':
            filters['is_return'] = 0
        for row in frappe.get_all(dt, filters=filters, fields=['name']):
            if exclude == (dt, row.name) or (dt == 'Sales Order' and row.name == linked_order):
                continue
            if dt == 'Sales Invoice' and exclude and exclude[0] == 'Sales Order' and frappe.db.exists('Sales Invoice Item', {'parent': row.name, 'sales_order': exclude[1]}):
                continue
            found.append((dt, row.name))
    if check_meter_readings and frappe.db.exists('Meter Reading', {'bill_structure_assignment': ('in', names), 'docstatus': 1, 'date': ('between', [first, last])}):
        frappe.throw(_('A submitted Meter Reading has already billed this customer and property for this month.'))
    return found


def populate_bill(doc, assignment, structure, date):
    from erpnext.controllers.accounts_controller import AccountsController
    context = frappe.new_doc('Meter Reading')  # Calculation context only; no reading is saved.
    context.date = date
    rates = calculate_rows(structure, context, None)
    if not rates:
        frappe.throw(_('The Bill Structure has no billable charges for this date.'))
    original = list(doc.get('items') or [])
    doc.set('items', [])
    for i, rate in enumerate(rates):
        values = dict(item_code=rate['item'], qty=rate['qty'], rate=rate['rate'])
        if doc.doctype == 'Sales Order':
            values['delivery_date'] = date
        if assignment.property:
            values['utility_property'] = assignment.property
        if i < len(original) and original[i].item_code == rate['item']:
            for key in ('sales_order', 'so_detail'):
                if original[i].get(key):
                    values[key] = original[i].get(key)
        doc.append('items', values)
    doc.ignore_pricing_rule = 1
    doc.fixed_utility_bill = 1
    doc.bill_structure_assignment = assignment.name
    doc.utility_billing_date = date
    if doc.doctype == 'Sales Invoice':
        doc.update_stock = 0  # Fixed stock-item accounting remains deferred.
    if not doc.get('selling_price_list'):
        customer = frappe.get_doc('Customer', assignment.customer)
        doc.selling_price_list = customer.default_price_list or frappe.db.get_value('Customer Group', customer.customer_group, 'default_price_list') or frappe.db.get_single_value('Selling Settings', 'selling_price_list')
    if not doc.get('currency'):
        doc.currency = frappe.db.get_value('Company', assignment.company, 'default_currency')
    AccountsController.append_taxes_from_item_tax_template(doc)


def validate_fixed_bill(doc, method=None):
    if not doc.get('fixed_utility_bill'):
        return
    if doc.doctype not in DATE_FIELDS:
        frappe.throw(_('Fixed utility billing supports Sales Orders and Sales Invoices.'))
    if doc.get('is_return'):
        return
    if not doc.get('bill_structure_assignment'):
        frappe.throw(_('Fixed utility bills require a Bill Structure Assignment.'))
    previous = frappe.get_doc('Utility Bill Structure Assignment', doc.bill_structure_assignment)
    if doc.customer != previous.customer or doc.company != previous.company:
        frappe.throw(_('The bill customer and company must match its assignment.'))
    orders = {row.get('sales_order') for row in doc.get('items') or [] if row.get('sales_order')}
    if len(orders) > 1:
        frappe.throw(_('A fixed utility invoice must come from one Sales Order.'))
    linked_order = next(iter(orders), None)
    date = doc.get(DATE_FIELDS[doc.doctype])
    if linked_order:
        order = frappe.get_doc('Sales Order', linked_order)
        if not order.get('fixed_utility_bill') or order.customer != doc.customer or order.company != doc.company:
            frappe.throw(_('The source Sales Order must be a fixed utility bill for this customer.'))
        date = order.utility_billing_date
    scope_lock(previous)
    resolved = assignment_for_date(doc.customer, doc.company, date, previous.property)
    if not resolved['name']:
        frappe.throw(_('No submitted assignment covers this billing date.'))
    assignment = frappe.get_doc('Utility Bill Structure Assignment', resolved['name'])
    structure = fixed_structure(assignment, date)
    duplicates = existing_bills(assignment, date, exclude=(doc.doctype, doc.name), linked_order=linked_order)
    if duplicates:
        frappe.throw(_('This customer and property already have a bill for this month: {0} {1}.').format(*duplicates[0]))
    populate_bill(doc, assignment, structure, date)


def create_bill(assignment, date, doctype='Sales Invoice', auto_repeat=None, ignore_permissions=False):
    if doctype not in DATE_FIELDS:
        frappe.throw(_('Choose Sales Invoice or Sales Order.'))
    fixed_structure(assignment, date)
    scope_lock(assignment)
    existing = existing_bills(assignment, date)
    if existing:
        dt, name = existing[0]
        bill = frappe.get_doc(dt, name)
        if dt != doctype or bill.bill_structure_assignment != assignment.name:
            frappe.throw(_('This billing month already belongs to another bill.'))
        return bill
    doc = frappe.new_doc(doctype)
    doc.customer, doc.company = assignment.customer, assignment.company
    doc.fixed_utility_bill = 1
    doc.bill_structure_assignment = assignment.name
    doc.set(DATE_FIELDS[doctype], date)
    if doctype == 'Sales Invoice':
        doc.set_posting_time = 1
        doc.due_date = date
    doc.auto_repeat = auto_repeat
    doc.insert(ignore_permissions=ignore_permissions)
    return doc


def start_billing(assignment, billing_date=None, reference_doctype='Sales Invoice'):
    assignment.check_permission('write')
    frappe.has_permission(reference_doctype, 'create', throw=True)
    frappe.has_permission('Auto Repeat', 'create', throw=True)
    date = getdate(billing_date or today())
    fixed_structure(assignment, date)
    scope_lock(assignment)
    schedule_name = frappe.db.get_value(assignment.doctype, assignment.name, 'billing_auto_repeat')
    if schedule_name:
        repeat = frappe.get_doc('Auto Repeat', schedule_name)
        repeat.check_permission('read')
        return dict(doctype=repeat.reference_doctype, name=repeat.reference_document, auto_repeat=repeat.name)
    bill = create_bill(assignment, date, reference_doctype)
    repeat = frappe.get_doc(dict(doctype='Auto Repeat', reference_doctype=bill.doctype,
        reference_document=bill.name, bill_structure_assignment=assignment.name,
        start_date=date, end_date=assignment.end_date, frequency='Monthly', repeat_on_day=date.day,
        submit_on_creation=0, notify_by_email=0))
    # If only the first month remains, retain a disabled history record rather than an invalid schedule.
    next_date = repeat.get_next_schedule_date(schedule_date=date)
    if assignment.end_date and getdate(next_date) > getdate(assignment.end_date):
        repeat.disabled = 1
    if repeat.disabled and repeat.end_date and getdate(repeat.end_date) in (date, getdate(today())):
        repeat.end_date = None
    repeat.insert()
    assignment.db_set('billing_auto_repeat', repeat.name)
    return dict(doctype=bill.doctype, name=bill.name, auto_repeat=repeat.name)


def recurring_bill(repeat):
    frappe.has_permission(repeat.reference_doctype, 'create', user=repeat.owner, throw=True)
    if repeat.disabled:
        frappe.throw(_('This billing schedule is disabled.'))
    assignment = frappe.get_doc('Utility Bill Structure Assignment', repeat.bill_structure_assignment)
    date = getdate(repeat.next_schedule_date)
    bill = create_bill(assignment, date, repeat.reference_doctype, repeat.name, ignore_permissions=True)
    if repeat.submit_on_creation and bill.docstatus == 0:
        frappe.has_permission(repeat.reference_doctype, 'submit', user=repeat.owner, throw=True)
        bill.submit()
    return bill


def sync_schedule_end(assignment):
    if not assignment.get('billing_auto_repeat'):
        return
    repeat = frappe.get_doc('Auto Repeat', assignment.billing_auto_repeat)
    repeat.end_date = assignment.end_date
    if assignment.docstatus == 2 or (assignment.end_date and (
        getdate(assignment.end_date) < getdate(today()) or
        (repeat.next_schedule_date and getdate(repeat.next_schedule_date) > getdate(assignment.end_date)))):
        repeat.disabled = 1
    if repeat.disabled and repeat.end_date and getdate(repeat.end_date) in (getdate(repeat.start_date), getdate(today())):
        repeat.end_date = None
    repeat.save()


def validate_assignment_end(assignment):
    if not assignment.end_date:
        return
    for dt in DATE_FIELDS:
        if frappe.db.exists(dt, {'bill_structure_assignment': assignment.name, 'fixed_utility_bill': 1,
            'docstatus': ('<', 2), 'utility_billing_date': ('>', assignment.end_date)}):
            frappe.throw(_('End Date cannot exclude an existing fixed utility bill.'))
