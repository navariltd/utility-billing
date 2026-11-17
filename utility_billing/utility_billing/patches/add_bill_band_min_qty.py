"""Preserve existing (previous maximum, maximum] ranges when adding Min Qty."""
import frappe
from frappe.utils import flt


def execute():
    previous = {}
    for band in frappe.get_all('Utility Bill Band', fields=['name', 'parent', 'item', 'upper_limit'], order_by='parent, idx'):
        key = (band.parent, band.item or '')
        frappe.db.set_value('Utility Bill Band', band.name, 'min_qty', previous.get(key, 0), update_modified=False)
        previous[key] = flt(band.upper_limit)
