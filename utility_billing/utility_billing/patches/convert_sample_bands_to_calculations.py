"""Upgrade the explicitly created, unbilled sample structures to progressive formulas."""
import frappe


def execute():
    from utility_billing.utility_billing.patches.demo.formula_billing import sample_structures

    for name, values in sample_structures().items():
        if not frappe.db.exists('Utility Bill Structure', name):
            continue
        doc = frappe.get_doc('Utility Bill Structure', name)
        if doc.company != 'Mwangaza Water Services':
            continue
        if not doc.get('bands') and not any(row.get('row_type') == 'Calculation Only' for row in doc.items):
            continue
        assignments = frappe.get_all('Utility Bill Structure Assignment', filters={'utility_bill_structure': name}, pluck='name')
        if assignments and frappe.db.exists('Meter Reading', {'bill_structure_assignment': ('in', assignments), 'docstatus': 1}):
            # A billed structure is historical: create a new structure/assignment to change its pricing.
            continue
        for field, value in values.items():
            doc.set(field, value)
        doc.validate()
        doc.flags.ignore_validate_update_after_submit = True
        doc.save()
        if assignments:
            for reading_name in frappe.get_all('Meter Reading', filters={'bill_structure_assignment': ('in', assignments), 'docstatus': 0}, pluck='name'):
                frappe.get_doc('Meter Reading', reading_name).save()
