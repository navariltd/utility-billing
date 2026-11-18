"""Replace known example formulas with equivalent, consultant-friendly expressions."""
import frappe


def replacements():
    old_portions = ['min(consumption, 10)', 'min(max(consumption - 10, 0), 10)', 'max(consumption - 20, 0)']
    changes = {}
    for rates in [(10, 8, 6), (5, 4, 3)]:
        amounts = [
            f'consumption * {rates[0]} if consumption <= 10 else 10 * {rates[0]}',
            f'0 if consumption <= 10 else ((consumption - 10) * {rates[1]} if consumption <= 20 else 10 * {rates[1]})',
            f'(consumption - 20) * {rates[2]} if consumption > 20 else 0',
        ]
        for old, rate, expression in zip(old_portions, rates, amounts):
            changes[f'{old} * {rate}'] = expression
    changes['max(water_total * 0.2, 50)'] = 'water_total * 0.2 if water_total * 0.2 >= 50 else 50'
    return changes


def execute():
    changes = replacements()
    for row in frappe.get_all('Utility Bill Structure Item', fields=['name', 'formula']):
        updated = {field: changes[row[field]] for field in ('formula',) if row.get(field) in changes}
        if updated:
            frappe.db.set_value('Utility Bill Structure Item', row.name, updated, update_modified=False)
    # Refresh draft explanations only. Submitted bills keep the formulas recorded when billed.
    drafts = set(frappe.get_all('Meter Reading', filters={'docstatus': 0}, pluck='name'))
    for row in frappe.get_all('Bill Calculation', fields=['name', 'parent', 'formula']):
        if row.parent in drafts and row.formula in changes:
            frappe.db.set_value('Bill Calculation', row.name, 'formula', changes[row.formula], update_modified=False)
    frappe.clear_cache(doctype='Utility Bill Structure')
