"""Restricted numeric expressions for Bill Structure item rows."""
import ast
import calendar
import math
import re

import frappe
from frappe import _
from frappe.utils import flt, getdate

FUNCTIONS = {'min': min, 'max': max, 'round': round, 'abs': abs}
VARIABLES = {'consumption', 'current_reading', 'previous_reading', 'amount', 'band_rate', 'days_in_month'}
ALLOWED = (ast.Expression, ast.Constant, ast.Name, ast.Load, ast.BinOp, ast.UnaryOp, ast.BoolOp,
           ast.Compare, ast.IfExp, ast.Call, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv,
           ast.Mod, ast.UAdd, ast.USub, ast.Not, ast.And, ast.Or, ast.Eq, ast.NotEq, ast.Lt,
           ast.LtE, ast.Gt, ast.GtE)


def parse_expression(expression, names):
    if len(expression) > 1000:
        raise ValueError('Expression is too long')
    tree = ast.parse(expression, mode='eval')
    for node in ast.walk(tree):
        if not isinstance(node, ALLOWED):
            raise ValueError('Use numeric expressions and supported functions only')
        if isinstance(node, ast.Constant) and not isinstance(node.value, (int, float, bool)):
            raise ValueError('Only numeric constants are allowed')
        if isinstance(node, ast.Name) and node.id not in names | FUNCTIONS.keys():
            raise ValueError(f'Unknown variable: {node.id}')
        if isinstance(node, ast.Call) and (not isinstance(node.func, ast.Name) or node.func.id not in FUNCTIONS or node.keywords):
            raise ValueError('Unsupported function')
    return tree


def validate_formulas(structure):
    names = set(VARIABLES)
    earlier_calculations = {}
    for row in structure.items:
        try:
            if row.get('row_type') == 'Calculation Only':
                row.item = None
                if not row.get('label') or not row.get('abbreviation'):
                    raise ValueError('Calculation-only rows require a Description and Abbreviation')
                if flt(row.get('discount')):
                    raise ValueError('Discounts apply to billable items only')
            elif not row.get('item'):
                raise ValueError('Select an Item for every billable row')
            for key in ('condition', 'formula', 'quantity_formula'):
                expression = row.get(key)
                if expression:
                    parse_expression(expression, names)
            if row.get('calculation_type') == 'Formula' and not row.get('formula'):
                raise ValueError('Amount Formula is required')
            sources = quantity_sources(row)
            for code in sources:
                helper = earlier_calculations.get(code)
                if not helper or not helper.get('quantity_formula'):
                    raise ValueError(f'Stock quantity source {code} must be an earlier calculation-only row with a Quantity Formula')
            code = row.get('abbreviation')
            if code:
                if not re.fullmatch('[A-Za-z][A-Za-z0-9_]*', code) or code in names or code in FUNCTIONS:
                    raise ValueError('Abbreviation must be a unique variable name')
                names.add(code)
                if row.get('row_type') == 'Calculation Only':
                    earlier_calculations[code] = row
        except (ValueError, SyntaxError) as exc:
            frappe.throw(_('Bill Structure row {0}: {1}').format(row.idx, str(exc)))

    if structure.items and all(row.get('row_type') == 'Calculation Only' for row in structure.items):
        frappe.throw(_('Add at least one billable item to the Bill Structure.'))


def evaluate(expression, context):
    parse_expression(expression, set(context))
    result = frappe.safe_eval(expression, eval_globals=FUNCTIONS, eval_locals=context)
    if not isinstance(result, (int, float, bool)) or not math.isfinite(result):
        raise ValueError('Expression must return a finite number')
    return result


def calculate_rows(structure, reading, source):
    context = dict(consumption=flt(source.consumption) if source else 0,
        current_reading=flt(source.current_reading) if source else 0,
        previous_reading=flt(source.previous_reading) if source else 0,
        days_in_month=calendar.monthrange(getdate(reading.date).year, getdate(reading.date).month)[1])
    results = []
    reading.set('calculations', [])
    quantities = {}
    used_sources = set()
    stock_consumption_qty = 0
    check_consumption_qty = bool(source and frappe.get_cached_value('Item', source.item_code, 'is_stock_item') and any(
        row.get('row_type') != 'Calculation Only' and row.get('calculation_type') == 'Formula' and row.item == source.item_code
        for row in structure.items))
    for row in structure.items:
        try:
            local = dict(context, amount=flt(row.amount), band_rate=0)
            expressions = [row.get(k) or '' for k in ('condition', 'formula', 'quantity_formula')]
            uses_band = any(any(isinstance(n, ast.Name) and n.id == 'band_rate' for n in ast.walk(ast.parse(e, mode='eval'))) for e in expressions if e)
            # Conditions can skip a charge before its tariff is needed.
            if row.get('condition') and 'band_rate' not in row.condition and not evaluate(row.condition, local):
                if row.get('abbreviation'):
                    context[row.abbreviation] = 0
                    quantities[row.abbreviation] = dict(qty=0, amount=0)
                append_calculation(reading, row, 0, False)
                continue
            if uses_band:
                bands = [b for b in structure.bands if b.get('item') == row.item]
                from .structure_billing import band_for_consumption
                match = band_for_consumption(bands, context['consumption'])
                if not match:
                    raise ValueError('No matching consumption band for this item')
                local['band_rate'] = flt(match.rate)
            if row.get('condition') and not evaluate(row.condition, local):
                if row.get('abbreviation'):
                    context[row.abbreviation] = 0
                    quantities[row.abbreviation] = dict(qty=0, amount=0)
                append_calculation(reading, row, 0, False)
                continue
            amount = evaluate(row.formula, local) if row.get('calculation_type') == 'Formula' else flt(row.amount)
            calculation_only = row.get('row_type') == 'Calculation Only'
            gross_amount = amount
            factor = 1 - flt(row.discount) / 100 if not calculation_only else 1
            amount *= factor
            if amount < 0 or not math.isfinite(amount):
                raise ValueError('Amount must be finite and nonnegative')
            if row.get('abbreviation'): context[row.abbreviation] = amount
            if calculation_only:
                qty = evaluate(row.quantity_formula, local) if row.get('quantity_formula') else None
                if qty is not None and (qty < 0 or (qty == 0 and amount != 0)):
                    raise ValueError('Tier quantity must be nonnegative; nonzero tier amounts require a quantity')
                if row.get('abbreviation'):
                    quantities[row.abbreviation] = dict(qty=qty, amount=amount)
                append_calculation(reading, row, amount, True, qty)
                continue
            if row.get('calculation_type') != 'Formula':
                results.append(dict(item=row.item, qty=1, rate=amount))
                append_calculation(reading, row, amount, True, 1)
                continue
            stock_item = bool(frappe.get_cached_value('Item', row.item, 'is_stock_item'))
            if stock_item:
                sources = quantity_sources(row)
                if sources:
                    portions = []
                    for code in sources:
                        if (row.item, code) in used_sources:
                            raise ValueError(f'Stock quantity source {code} was already used for this item')
                        portion = quantities.get(code)
                        if not portion or portion['qty'] is None:
                            raise ValueError(f'Stock quantity source {code} requires a tier Quantity Formula')
                        portions.append(portion)
                        used_sources.add((row.item, code))
                    if not math.isclose(sum(p['amount'] for p in portions), gross_amount, rel_tol=1e-9, abs_tol=1e-8):
                        raise ValueError('Stock quantity source amounts must add up to the billable amount')
                    qty = sum(p['qty'] for p in portions)
                    for portion in portions:
                        if portion['qty']:
                            results.append(dict(item=row.item, qty=portion['qty'], rate=portion['amount'] * factor / portion['qty']))
                else:
                    if not row.get('quantity_formula'):
                        raise ValueError('Stock items require a Quantity Formula or Stock Quantity Sources')
                    qty = evaluate(row.quantity_formula, local)
                    if qty < 0 or (qty == 0 and amount != 0):
                        raise ValueError('Stock quantity must be nonnegative; nonzero amounts require a quantity')
                    if qty:
                        results.append(dict(item=row.item, qty=qty, rate=amount / qty))
            else:
                qty = 1
                results.append(dict(item=row.item, qty=1, rate=amount))
            if stock_item and source and row.item == source.item_code:
                stock_consumption_qty += qty
            append_calculation(reading, row, amount, True, qty)
        except Exception as exc:
            frappe.throw(_('Bill Structure row {0} ({1}): {2}').format(row.idx, row.get('label') or row.get('item') or row.get('abbreviation'), str(exc)))
    if check_consumption_qty:
        if not math.isclose(stock_consumption_qty, context['consumption'], rel_tol=1e-9, abs_tol=1e-8):
            frappe.throw(_('Stock quantities for the consumption item must add up to the meter consumption.'))
    return results


def append_calculation(reading, row, amount, applied, qty=None):
    reading.append('calculations', dict(label=row.get('label') or row.get('item'),
        row_type=row.get('row_type') or 'Billable Item', abbreviation=row.get('abbreviation'),
        amount=amount, qty=qty, rate=amount / qty if qty else 0, applied=int(applied),
        formula=row.get('formula') if row.get('calculation_type') == 'Formula' else None))


def quantity_sources(row):
    sources = [code.strip() for code in (row.get('stock_quantity_sources') or '').split(',') if code.strip()]
    if len(sources) != len(set(sources)):
        raise ValueError('Stock Quantity Sources cannot contain duplicate abbreviations')
    return sources
