"""Whole-consumption band billing, separate from progressive Item Price tariffs."""
import frappe
from frappe import _
from frappe.utils import flt, getdate, get_first_day, get_last_day


def band_contains(band, consumption):
    minimum = flt(band.get('min_qty'))
    return (consumption > minimum or minimum == consumption == 0) and consumption <= flt(band.upper_limit)


def band_for_consumption(bands, consumption):
    matches = [band for band in bands if band_contains(band, consumption)]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        frappe.throw(_('More than one consumption band matches this quantity.'))
    frappe.throw(_('No consumption band matches this quantity.'))


def structure_rates(reading):
    if not reading.get('bill_structure_assignment'):
        return False
    assignment = frappe.get_doc('Utility Bill Structure Assignment', reading.bill_structure_assignment)
    assignment.check_permission('read')
    if assignment.docstatus != 1:
        frappe.throw(_('Bill Structure Assignment must be submitted.'))
    for key in ('customer', 'company', 'property'):
        if (assignment.get(key) or '') != (reading.get(key) or ''):
            frappe.throw(_('Reading {0} must match its assignment.').format(key))
    date = getdate(reading.date)
    if date < getdate(assignment.start_date) or (assignment.end_date and date > getdate(assignment.end_date)):
        frappe.throw(_('Reading date is outside the assignment period.'))
    structure = frappe.get_doc('Utility Bill Structure', assignment.utility_bill_structure)
    if structure.docstatus != 1:
        frappe.throw(_('Bill Structure must be submitted.'))
    if (structure.start_date and date < getdate(structure.start_date)) or (structure.end_date and date > getdate(structure.end_date)):
        frappe.throw(_('Reading date is outside the Bill Structure period.'))
    reading.set('rates', [])
    from .billing_formula import calculate_rows
    source = None
    if structure.metered_billing:
        if len(reading.items) != 1 or reading.items[0].item_code != structure.water_item:
            frappe.throw(_('Enter exactly one reading for the consumption item in the Bill Structure.'))
        source = reading.items[0]
    elif reading.items:
        frappe.throw(_('This Bill Structure does not require meter reading items.'))
    # Previously configured metered structures continue to work until amended.
    legacy_bands = structure.bands and all(not b.get('item') for b in structure.bands)
    if structure.metered_billing and legacy_bands:
        qty = flt(source.consumption)
        band = band_for_consumption(structure.bands, qty)
        if qty:
            append_rate(reading, structure.water_item, qty, band.water_rate, source)
            if structure.sewerage_item:
                append_rate(reading, structure.sewerage_item, qty, band.sewerage_rate, source)
    for result in calculate_rows(structure, reading, source):
        append_rate(reading, result['item'], result['qty'], result['rate'], source)
    return True


def append_rate(reading, item, qty, rate, source=None):
    reading.append('rates', dict(item_code=item, qty=qty, rate=rate, amount=qty * flt(rate),
        meter_reading_item=source.name if source else None,
        warehouse=source.warehouse if source else reading.warehouse))


def check_monthly_duplicate(reading):
    if not reading.get('bill_structure_assignment'):
        return
    # Serialize submissions for this assignment before checking the billing month.
    frappe.db.get_value('Utility Bill Structure Assignment', reading.bill_structure_assignment, 'name', for_update=True)
    if frappe.db.exists('Meter Reading', {
        'bill_structure_assignment': reading.bill_structure_assignment,
        'docstatus': 1, 'name': ('!=', reading.name),
        'date': ('between', [get_first_day(reading.date), get_last_day(reading.date)]),
    }):
        frappe.throw(_('This assignment has already been billed for this month.'))


def previous_assigned_reading(reading, item, fallback):
    """Include submitted readings even when their Sales Order is not invoiced yet."""
    rows = frappe.db.sql('''
        select i.current_reading, r.date
        from `tabMeter Reading Item` i
        inner join `tabMeter Reading` r on r.name = i.parent
        where r.docstatus = 1 and r.customer = %s and r.company = %s
          and i.item_code = %s and coalesce(i.meter_number, '') = %s
          and coalesce(r.property, '') = %s and r.name != %s
        order by r.date desc, r.creation desc limit 1
    ''', (reading.customer, reading.company, item.item_code, item.meter_number or '',
          reading.property or '', reading.name or ''), as_dict=True)
    if not rows:
        return fallback
    if getdate(rows[0].date) >= getdate(reading.date):
        frappe.throw(_('Enter readings in chronological order.'))
    return rows[0].current_reading


@frappe.whitelist()
def assignment_for_date(customer, company=None, reading_date=None, property=None):
    """Resolve the effective assignment using the reading's date, never today's date."""
    if not frappe.has_permission('Meter Reading', 'create') and not frappe.has_permission('Meter Reading', 'write'):
        frappe.throw(_('Not permitted to create or edit Meter Readings.'), frappe.PermissionError)
    result = dict(name=None, has_assignments=False)
    if not customer or not company or not reading_date:
        return result
    date = getdate(reading_date)
    assignments = frappe.get_all('Utility Bill Structure Assignment',
        filters={'customer': customer, 'company': company, 'docstatus': 1},
        fields=['name', 'property', 'start_date', 'end_date', 'utility_bill_structure'],
        order_by='start_date desc')
    scoped = [a for a in assignments if (a.property or '') == (property or '')]
    result['has_assignments'] = bool(scoped)
    matches = [a for a in scoped if getdate(a.start_date) <= date and (not a.end_date or date <= getdate(a.end_date))]
    if len(matches) > 1:
        frappe.throw(_('Multiple submitted Bill Structure Assignments cover this reading date. Correct their overlapping dates.'))
    if matches:
        assignment = frappe.get_doc('Utility Bill Structure Assignment', matches[0].name)
        assignment.check_permission('read')
        structure = frappe.get_doc('Utility Bill Structure', assignment.utility_bill_structure)
        structure.check_permission('read')
        result.update(name=assignment.name, metered_billing=structure.metered_billing, consumption_item=structure.water_item)
    return result


def set_assignment_for_date(reading):
    previous = reading.get('bill_structure_assignment')
    result = assignment_for_date(reading.customer, reading.company, reading.date, reading.get('property'))
    reading.bill_structure_assignment = result['name']
    if not result['name'] and (result['has_assignments'] or previous):
        frappe.throw(_('No submitted Bill Structure Assignment covers this customer, company, property and reading date.'))
