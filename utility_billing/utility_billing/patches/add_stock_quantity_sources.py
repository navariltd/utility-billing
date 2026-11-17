"""Add tier quantities to the unbilled sample structures without changing their tariffs."""
import frappe


def execute():
    from utility_billing.utility_billing.patches.demo.formula_billing import sample_structures

    for name, values in sample_structures().items():
        if not frappe.db.exists('Utility Bill Structure', name):
            continue
        doc = frappe.get_doc('Utility Bill Structure', name)
        if doc.company != 'Mwangaza Water Services':
            continue
        assignments = frappe.get_all('Utility Bill Structure Assignment', filters={'utility_bill_structure': name}, pluck='name')
        if assignments and frappe.db.exists('Meter Reading', {'bill_structure_assignment': ('in', assignments), 'docstatus': 1}):
            continue
        expected = {row.get('abbreviation'): row for row in values['items'] if row.get('abbreviation')}
        changed = False
        for row in doc.items:
            template = expected.get(row.abbreviation)
            if not template or row.formula != template.get('formula'):
                continue
            for field in ('quantity_formula', 'stock_quantity_sources'):
                if template.get(field) and row.get(field) != template[field]:
                    row.set(field, template[field])
                    changed = True
        if changed:
            doc.validate()
            doc.flags.ignore_validate_update_after_submit = True
            doc.save()
            if assignments:
                for reading_name in frappe.get_all('Meter Reading', filters={'bill_structure_assignment': ('in', assignments), 'docstatus': 0}, pluck='name'):
                    frappe.get_doc('Meter Reading', reading_name).save()
