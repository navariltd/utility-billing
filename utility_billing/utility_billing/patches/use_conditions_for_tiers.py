"""Move sample tier applicability into Condition without changing charges."""
import frappe


def execute():
    from utility_billing.utility_billing.patches.demo.formula_billing import sample_structures
    changed = []
    for name, values in sample_structures().items():
        if not frappe.db.exists('Utility Bill Structure', name):
            continue
        structure = frappe.get_doc('Utility Bill Structure', name)
        if structure.company != 'Mwangaza Water Services':
            continue
        templates = {row.get('abbreviation'): row for row in values['items'] if row.get('row_type') == 'Calculation Only'}
        for row in structure.items:
            template = templates.get(row.abbreviation)
            if not template or row.get('row_type') != 'Calculation Only':
                continue
            formula = template['formula']
            if row.abbreviation.endswith('2'):
                original = f'0 if consumption <= 10 else ({formula})'
            elif row.abbreviation.endswith('3'):
                original = f'{formula} if consumption > 20 else 0'
            else:
                original = formula
            if row.formula not in (original, formula) or row.condition not in (None, '', template['condition']):
                continue  # Preserve consultant changes to rates or conditions.
            frappe.db.set_value('Utility Bill Structure Item', row.name,
                {'formula': formula, 'condition': template['condition']}, update_modified=False)
            changed.append(name)
    frappe.clear_cache(doctype='Utility Bill Structure')
    return sorted(set(changed))
