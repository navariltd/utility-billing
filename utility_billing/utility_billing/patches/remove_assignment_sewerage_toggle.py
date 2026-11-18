"""Make the structure's configured charges authoritative, including saved expressions."""
import ast

import frappe


class RemoveSewerageToggle(ast.NodeTransformer):
    def visit_Name(self, node):
        if node.id == 'include_sewerage':
            return ast.copy_location(ast.Constant(value=True), node)
        return node


def migrate_expression(expression, condition=False):
    if not expression or 'include_sewerage' not in expression:
        return expression
    tree = ast.parse(expression, mode='eval')
    tree = ast.fix_missing_locations(RemoveSewerageToggle().visit(tree))
    if condition and isinstance(tree.body, ast.Constant) and tree.body.value is True:
        return ''
    return ast.unparse(tree)


def execute():
    for row in frappe.get_all('Utility Bill Structure Item', fields=['name', 'condition', 'formula']):
        changes = {}
        for field in ('condition', 'formula'):
            original = row.get(field)
            updated = migrate_expression(original, condition=field == 'condition')
            if updated != original:
                changes[field] = updated
        if changes:
            # Submitted structures keep their rates and history; only retire the removed flag.
            frappe.db.set_value('Utility Bill Structure Item', row.name, changes, update_modified=False)
    frappe.clear_cache(doctype='Utility Bill Structure')
