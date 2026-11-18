from unittest import TestCase
from unittest.mock import patch

import frappe

from utility_billing.utility_billing.utils.structure_billing import band_for_consumption, structure_rates, check_monthly_duplicate


class TestStructureBilling(TestCase):
    def setUp(self):
        self.structure = frappe.get_doc(dict(doctype='Utility Bill Structure', docstatus=1,
            company='_Test Company', metered_billing=1, water_item='Water', sewerage_item='Sewer',
            bands=[dict(upper_limit=10, water_rate=10, sewerage_rate=5),
                   dict(min_qty=10, upper_limit=20, water_rate=8, sewerage_rate=4)], items=[]))
        self.assignment = frappe.get_doc(dict(doctype='Utility Bill Structure Assignment', docstatus=1,
            customer='Customer', company='_Test Company', start_date='2026-01-01',
            end_date='2026-12-31', utility_bill_structure='Structure'))
        self.reading = frappe.get_doc(dict(doctype='Meter Reading', customer='Customer', company='_Test Company',
            date='2026-11-01', bill_structure_assignment='Assignment',
            items=[dict(item_code='Water', consumption=15, name='Reading Row')]))

    def rates(self, stock_items=()):
        with patch('frappe.get_doc', side_effect=[self.assignment, self.structure]), patch.object(self.assignment, 'check_permission'), patch('frappe.get_cached_value', side_effect=lambda dt, name, field: int(name in stock_items)):
            return structure_rates(self.reading)

    def test_whole_band_water_and_sewerage(self):
        self.rates()
        self.assertEqual([(r.item_code, r.qty, r.rate, r.amount) for r in self.reading.rates],
                         [('Water', 15, 8, 120), ('Sewer', 15, 4, 60)])

    def test_boundaries_and_decimal_consumption(self):
        for qty, expected in [(0, 10), (10, 10), (10.01, 8), (20, 8)]:
            self.assertEqual(band_for_consumption(self.structure.bands, qty).water_rate, expected)
        with self.assertRaises(frappe.ValidationError):
            band_for_consumption(self.structure.bands, 21)

    def test_water_only(self):
        self.structure.sewerage_item = None
        self.rates()
        self.assertEqual(len(self.reading.rates), 1)

    def test_fixed_monthly_with_discount(self):
        self.structure.metered_billing = 0
        self.structure.append('items', dict(item='Fixed Water', amount=500, discount=10))
        self.reading.set('items', [])
        self.rates()
        self.assertEqual([(r.qty, r.rate, r.amount) for r in self.reading.rates], [(1, 450, 450)])

    def test_assignment_scope_and_dates(self):
        for key, value in [('customer', 'Other'), ('company', 'Other'), ('date', '2027-01-01')]:
            old = self.reading.get(key)
            self.reading.set(key, value)
            with self.assertRaises(frappe.ValidationError):
                self.rates()
            self.reading.set(key, old)

    def test_legacy_path(self):
        self.reading.bill_structure_assignment = None
        self.assertFalse(structure_rates(self.reading))

    def test_duplicate_month(self):
        with patch.object(frappe.db, 'get_value'), patch.object(frappe.db, 'exists', return_value=True), patch('frappe.get_doc', return_value=self.assignment), patch('utility_billing.utility_billing.utils.fixed_billing.scope_lock'), patch('utility_billing.utility_billing.utils.fixed_billing.existing_bills', return_value=[]):
            with self.assertRaises(frappe.ValidationError):
                check_monthly_duplicate(self.reading)

    def test_invalid_bands(self):
        self.structure.bands[1].upper_limit = 10
        with self.assertRaises(frappe.ValidationError):
            self.structure.validate()

    def test_generic_formulas_and_extra_item(self):
        self.structure.set('bands', [dict(item='Water', min_qty=0, upper_limit=20, rate=8), dict(item='Sewer', min_qty=0, upper_limit=20, rate=4)])
        self.structure.set('items', [
            dict(item='Water', abbreviation='water_total', calculation_type='Formula', formula='consumption * band_rate'),
            dict(item='Sewer', calculation_type='Formula', formula='consumption * band_rate'),
            dict(item='Other Service', calculation_type='Formula', formula='max(water_total * 0.1, 20)')])
        self.structure.validate()
        self.rates()
        self.assertEqual([r.amount for r in self.reading.rates], [120, 60, 20])
        self.structure.items[1].condition = '0'
        self.rates()
        self.assertEqual([r.amount for r in self.reading.rates], [120, 20])

    def test_invalid_and_unsafe_formulas(self):
        from utility_billing.utility_billing.utils.billing_formula import evaluate
        for expr in ['consumption.__class__', '__import__(1)', '[x for x in (1, 2)]', 'unknown + 1', '2 ** 100000', '1 / 0']:
            with self.assertRaises(Exception):
                evaluate(expr, {'consumption': 10})

    def test_formula_runtime_errors(self):
        self.structure.set('bands', [])
        self.structure.set('items', [dict(item='Water', calculation_type='Formula', formula='consumption * band_rate')])
        with self.assertRaises(frappe.ValidationError):
            self.rates()
        self.structure.items[0].formula = '-1'
        with self.assertRaises(frappe.ValidationError):
            self.rates()

    def test_formula_reference_order(self):
        self.structure.set('items', [dict(item='Water', calculation_type='Formula', formula='later * 2'),
                                   dict(item='Sewer', abbreviation='later', amount=5)])
        with self.assertRaises(frappe.ValidationError):
            self.structure.validate()


    def test_explicit_range_boundaries_and_gaps(self):
        self.structure.bands[0].min_qty = 0
        self.structure.bands[1].min_qty = 10
        for qty, rate in [(0, 10), (10, 10), (10.001, 8), (20, 8)]:
            self.assertEqual(band_for_consumption(self.structure.bands, qty).water_rate, rate)
        self.structure.bands[1].min_qty = 12
        with self.assertRaises(frappe.ValidationError):
            band_for_consumption(self.structure.bands, 11)
        self.assertEqual(band_for_consumption(self.structure.bands, 13).water_rate, 8)

    def test_overlapping_ranges_rejected(self):
        self.structure.bands[1].min_qty = 9
        with self.assertRaises(frappe.ValidationError):
            self.structure.validate()

    def test_invalid_minimum_rejected(self):
        for minimum in (-1, 10, 11):
            self.structure.bands[0].min_qty = minimum
            with self.assertRaises(frappe.ValidationError):
                self.structure.validate()

    def test_range_lookup_independent_of_row_order(self):
        self.structure.bands[1].min_qty = 10
        self.structure.set('bands', list(reversed(self.structure.bands)))
        self.structure.validate()
        self.assertEqual(band_for_consumption(self.structure.bands, 5).water_rate, 10)
        self.assertEqual(band_for_consumption(self.structure.bands, 15).water_rate, 8)


    def resolve_assignment(self, date, assignments, property=None):
        from utility_billing.utility_billing.utils.structure_billing import assignment_for_date
        def get_document(doctype, name):
            if doctype == 'Utility Bill Structure Assignment':
                self.assignment.name = name
                return self.assignment
            return self.structure
        with patch('frappe.has_permission', return_value=True), patch('frappe.get_all', return_value=assignments) as query, patch('frappe.get_doc', side_effect=get_document), patch.object(self.assignment, 'check_permission'), patch.object(self.structure, 'check_permission'):
            result = assignment_for_date('Customer', '_Test Company', date, property)
            self.assertEqual(query.call_args.kwargs['filters'], {'customer': 'Customer', 'company': '_Test Company', 'docstatus': 1})
            return result

    def test_assignment_uses_reading_date_and_inclusive_boundaries(self):
        old = frappe._dict(name='old', property=None, start_date='2026-10-01', end_date='2026-10-31')
        new = frappe._dict(name='new', property=None, start_date='2026-11-01', end_date=None)
        for date, expected in [('2026-10-01', 'old'), ('2026-10-31', 'old'), ('2026-11-01', 'new'), ('2027-01-01', 'new')]:
            self.assignment.name = expected
            self.assertEqual(self.resolve_assignment(date, [new, old])['name'], expected)
        result = self.resolve_assignment('2026-09-30', [new, old])
        self.assertIsNone(result['name'])
        self.assertTrue(result['has_assignments'])

    def test_assignment_property_and_overlap(self):
        first = frappe._dict(name='one', property='Building A', start_date='2026-01-01', end_date=None)
        second = frappe._dict(name='two', property='Building B', start_date='2026-01-01', end_date=None)
        self.assignment.name = 'one'
        self.assertEqual(self.resolve_assignment('2026-11-01', [first, second], 'Building A')['name'], 'one')
        self.assertIsNone(self.resolve_assignment('2026-11-01', [first, second])['name'])
        with self.assertRaises(frappe.ValidationError):
            self.resolve_assignment('2026-11-01', [first, first], 'Building A')

    def test_server_replaces_stale_assignment_and_rejects_gap(self):
        from utility_billing.utility_billing.utils.structure_billing import set_assignment_for_date
        self.reading.bill_structure_assignment = 'wrong-assignment'
        with patch('utility_billing.utility_billing.utils.structure_billing.assignment_for_date', return_value=dict(name='correct-assignment', has_assignments=True)):
            set_assignment_for_date(self.reading)
        self.assertEqual(self.reading.bill_structure_assignment, 'correct-assignment')
        with patch('utility_billing.utility_billing.utils.structure_billing.assignment_for_date', return_value=dict(name=None, has_assignments=True)):
            with self.assertRaises(frappe.ValidationError):
                set_assignment_for_date(self.reading)
        self.assertIsNone(self.reading.bill_structure_assignment)

    def test_unassigned_customer_keeps_legacy_pricing(self):
        from utility_billing.utility_billing.utils.structure_billing import set_assignment_for_date
        self.reading.bill_structure_assignment = None
        with patch('utility_billing.utility_billing.utils.structure_billing.assignment_for_date', return_value=dict(name=None, has_assignments=False)):
            set_assignment_for_date(self.reading)
        self.assertIsNone(self.reading.bill_structure_assignment)


    def test_retired_sewerage_condition_migration(self):
        from utility_billing.utility_billing.patches.remove_assignment_sewerage_toggle import migrate_expression
        from utility_billing.utility_billing.utils.billing_formula import evaluate
        self.assertEqual(migrate_expression('include_sewerage', condition=True), '')
        expression = migrate_expression('include_sewerage and consumption > 10', condition=True)
        self.assertFalse(evaluate(expression, {'consumption': 5}))
        self.assertTrue(evaluate(expression, {'consumption': 15}))
        self.assertEqual(migrate_expression('consumption > 0', condition=True), 'consumption > 0')
        self.assertEqual(migrate_expression(expression, condition=True), expression)

    def test_removed_assignment_flag_is_not_a_formula_variable(self):
        self.structure.set('items', [dict(item='Sewer', calculation_type='Formula', formula='consumption', condition='include_sewerage')])
        with self.assertRaises(frappe.ValidationError):
            self.structure.validate()


    def use_progressive_structure(self):
        from utility_billing.utility_billing.patches.demo.formula_billing import progressive_rows
        self.structure.set('bands', [])
        self.structure.sewerage_item = None
        self.structure.set('items', progressive_rows('Water', 'W', (10, 8, 6), 'water_total') +
                           progressive_rows('Sewer', 'S', (5, 4, 3), 'sewer_total'))
        self.structure.validate()

    def test_progressive_portions_and_no_double_billing(self):
        self.use_progressive_structure()
        self.rates()
        self.assertEqual(len(self.reading.rates), 2)
        self.assertAlmostEqual(self.reading.rates[0].amount, 140)
        self.assertAlmostEqual(self.reading.rates[1].amount, 70)
        self.assertEqual([r.amount for r in self.reading.calculations], [100, 40, 0, 140, 50, 20, 0, 70])
        self.assertEqual(sum(r.row_type == 'Billable Item' for r in self.reading.calculations), 2)

    def test_progressive_boundaries_and_decimals(self):
        self.use_progressive_structure()
        for consumption, water in [(0, 0), (5, 50), (10, 100), (10.5, 104), (15, 140), (20, 180), (20.5, 183), (50, 360), (51, 366)]:
            self.reading.items[0].consumption = consumption
            self.rates()
            if consumption:
                self.assertAlmostEqual(self.reading.rates[0].amount, water)
            else:
                self.assertEqual(sum(row.amount for row in self.reading.rates), 0)
            self.assertEqual(len(self.reading.calculations), 8)

    def test_fixed_helpers_are_not_in_totals(self):
        self.structure.metered_billing = 0
        self.structure.set('bands', [])
        self.structure.set('items', [dict(row_type='Calculation Only', label='Monthly base', abbreviation='BASE', amount=500),
                                   dict(item='Water', calculation_type='Formula', formula='BASE')])
        self.structure.validate()
        self.assertEqual(self.structure.total_amount, 0)
        self.reading.set('items', [])
        self.rates()
        self.assertEqual(len(self.reading.rates), 1)
        self.assertEqual(self.reading.rates[0].amount, 500)

    def test_skipped_helper_gives_zero_to_following_rows(self):
        self.structure.metered_billing = 0
        self.structure.set('bands', [])
        self.structure.set('items', [dict(row_type='Calculation Only', label='Optional charge', abbreviation='OPTIONAL', amount=50, condition='0'),
                                   dict(item='Water', calculation_type='Formula', formula='100 + OPTIONAL')])
        self.reading.set('items', [])
        self.rates()
        self.assertEqual(self.reading.rates[0].amount, 100)
        self.assertEqual(self.reading.calculations[0].applied, 0)
        self.assertEqual(self.reading.calculations[0].amount, 0)

    def test_calculation_only_requires_a_name_and_code(self):
        self.structure.set('items', [dict(row_type='Calculation Only', amount=50), dict(item='Water', amount=100)])
        with self.assertRaises(frappe.ValidationError):
            self.structure.validate()
        self.structure.items[0].label = 'Fee'
        self.structure.items[0].abbreviation = 'FEE'
        self.structure.validate()
        self.assertIsNone(self.structure.items[0].item)
        self.structure.items[1].item = None
        with self.assertRaises(frappe.ValidationError):
            self.structure.validate()

    def test_service_charge_uses_final_progressive_water_amount(self):
        from utility_billing.utility_billing.patches.demo.formula_billing import sample_structures
        self.structure.set('bands', [])
        self.structure.set('items', sample_structures()['Water with Service Charge']['items'])
        self.rates()
        self.assertAlmostEqual(sum(r.amount for r in self.reading.rates), 190)
        self.reading.items[0].consumption = 50
        self.rates()
        self.assertAlmostEqual(sum(r.amount for r in self.reading.rates), 432)


    def test_stock_item_uses_tier_quantities(self):
        self.use_progressive_structure()
        self.rates(stock_items={'Water'})
        self.assertEqual([(r.item_code, r.qty, r.rate, r.amount) for r in self.reading.rates],
                         [('Water', 10, 10, 100), ('Water', 5, 8, 40), ('Sewer', 1, 70, 70)])
        self.assertEqual(self.reading.calculations[0].qty, 10)
        self.assertEqual(self.reading.calculations[1].qty, 5)
        self.assertEqual(self.reading.calculations[3].qty, 15)

    def test_nonstock_item_always_has_one_charge(self):
        self.use_progressive_structure()
        self.rates()
        self.assertEqual([(r.qty, r.rate) for r in self.reading.rates], [(1, 140), (1, 70)])

    def test_stock_decimal_and_zero_consumption(self):
        self.use_progressive_structure()
        for consumption in (0, 5, 10, 10.5, 15, 20, 25):
            self.reading.items[0].consumption = consumption
            self.rates(stock_items={'Water'})
            stock_rows = [r for r in self.reading.rates if r.item_code == 'Water']
            self.assertAlmostEqual(sum(r.qty for r in stock_rows), consumption)
            self.assertTrue(all(r.qty > 0 for r in stock_rows))

    def test_stock_sources_must_match_amount_and_quantity(self):
        self.use_progressive_structure()
        self.structure.items[3].formula = 'W1 + W2 + W3 + 10'
        with self.assertRaises(frappe.ValidationError):
            self.rates(stock_items={'Water'})
        self.structure.items[3].formula = 'W1 + W2 + W3'
        self.structure.items[1].formula = '1 * 8'
        self.structure.items[3].formula = 'W1 + W2 + W3'
        with self.assertRaises(frappe.ValidationError):
            self.rates(stock_items={'Water'})

    def test_stock_sources_require_prior_tier_quantities(self):
        self.use_progressive_structure()
        self.structure.items[0].formula = '100'
        with self.assertRaises(frappe.ValidationError):
            self.structure.validate()
        with self.assertRaises(frappe.ValidationError):
            self.rates(stock_items={'Water'})

    def test_calculated_stock_item_without_quantity_does_not_default_to_one(self):
        self.structure.metered_billing = 0
        self.structure.set('bands', [])
        self.structure.set('items', [dict(item='Water', calculation_type='Formula', formula='100')])
        self.reading.set('items', [])
        with self.assertRaises(frappe.ValidationError):
            self.rates(stock_items={'Water'})

    def test_duplicate_stock_sources_are_rejected(self):
        self.use_progressive_structure()
        self.structure.items[3].stock_quantity_sources = 'W1, W1, W2'
        with self.assertRaises(frappe.ValidationError):
            self.structure.validate()


    def test_conditional_formulas_preserve_existing_results(self):
        from utility_billing.utility_billing.patches.use_conditional_tier_formulas import replacements
        from utility_billing.utility_billing.utils.billing_formula import evaluate
        for old, new in replacements().items():
            for consumption in (0, 5, 10, 10.5, 15, 20, 20.5, 50, 51):
                context = dict(consumption=consumption, water_total=consumption * 10)
                self.assertAlmostEqual(evaluate(old, context), evaluate(new, context))
        self.use_progressive_structure()
        self.assertTrue(all('min(' not in row.formula and 'max(' not in row.formula for row in self.structure.items))


    def test_fixed_stock_charge_stays_one_quantity(self):
        self.structure.metered_billing = 0
        self.structure.set('bands', [])
        self.structure.set('items', [dict(item='Water', amount=500), dict(item='Sewer', amount=200)])
        self.reading.set('items', [])
        self.rates(stock_items={'Water', 'Sewer'})
        self.assertEqual([(r.qty, r.rate, r.amount) for r in self.reading.rates], [(1, 500, 500), (1, 200, 200)])

    def test_fixed_stock_charge_does_not_use_meter_quantity(self):
        self.structure.set('bands', [])
        self.structure.set('items', [dict(item='Water', amount=500)])
        self.rates(stock_items={'Water'})
        self.assertEqual([(r.qty, r.amount) for r in self.reading.rates], [(1, 500)])


    def test_amount_formula_supplies_stock_quantities(self):
        from utility_billing.utility_billing.utils.billing_formula import quantity_from_amount
        context = dict(consumption=15)
        self.assertEqual(quantity_from_amount('(consumption - 10) * 8', context), 5)
        self.assertEqual(quantity_from_amount('consumption * 10 if consumption <= 10 else 10 * 10', context), 10)
        self.assertEqual(quantity_from_amount('0 if consumption <= 20 else (consumption - 20) * 6', context), 0)
        self.assertIsNone(quantity_from_amount('140', context))
        self.assertIsNone(quantity_from_amount('consumption + 10', context))
        self.assertIsNone(quantity_from_amount('consumption * consumption', context))
        self.assertIsNone(quantity_from_amount('water_total * 8', dict(context, water_total=140)))



def run_checks():
    import unittest
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(TestStructureBilling))
    if not result.wasSuccessful():
        raise AssertionError("Billing checks failed")
    return {"tests": result.testsRun, "passed": True}


def run_integration_check():
    """Exercise persisted documents and Sales Order creation; roll back all sample data."""
    from frappe.utils import nowdate, getdate
    suffix = frappe.generate_hash(length=8)
    try:
        company = '_Test Company'
        currency = frappe.db.get_value('Company', company, 'default_currency')
        customer = frappe.get_doc(dict(doctype='Customer', customer_name='Billing Check ' + suffix,
                                      customer_type='Individual')).insert()
        warehouse = frappe.get_doc(dict(doctype='Warehouse', warehouse_name='Billing Check ' + suffix, company=company)).insert().name
        items = []
        for service in ('Water', 'Sewer'):
            item = frappe.get_doc(dict(doctype='Item', item_code=service + suffix,
                item_group=frappe.db.get_value('Item Group', {'is_group': 0}, 'name'),
                stock_uom='Nos', is_stock_item=0, is_sales_item=1)).insert()
            items.append(item.name)
        price_list = frappe.get_doc(dict(doctype='Price List', price_list_name='Billing Check ' + suffix, currency=currency, selling=1, enabled=1)).insert().name
        date = nowdate()
        fy = frappe.db.get_value('Fiscal Year', {'year_start_date': ('<=', date), 'year_end_date': ('>=', date)}, 'name')
        if not fy:
            year = getdate(date).year
            fy = frappe.get_doc(dict(doctype='Fiscal Year', year=str(year), year_start_date=f'{year}-01-01', year_end_date=f'{year}-12-31')).insert().name
        structure = frappe.get_doc(dict(doctype='Utility Bill Structure', naming_series='UBS-.YYYY.-',
            fiscal_year=fy, company=company, metered_billing=1, water_item=items[0], sewerage_item=items[1],
            bands=[dict(item=items[0], upper_limit=10, rate=10), dict(item=items[0], min_qty=10, upper_limit=20, rate=8),
                   dict(item=items[1], upper_limit=10, rate=5), dict(item=items[1], min_qty=10, upper_limit=20, rate=4)],
            items=[dict(item=items[0], calculation_type='Formula', formula='consumption * band_rate'),
                   dict(item=items[1], calculation_type='Formula', formula='consumption * band_rate')])).insert()
        structure.submit()
        assignment = frappe.get_doc(dict(doctype='Utility Bill Structure Assignment', customer=customer.name,
            company=company, utility_bill_structure=structure.name, start_date=date)).insert()
        assignment.submit()
        frappe.db.set_single_value('Utility Billing Settings', 'sales_order_creation_state', 'Draft')
        reading = frappe.get_doc(dict(doctype='Meter Reading', customer=customer.name, company=company,
            currency=currency, price_list=price_list, warehouse=warehouse, date=date,
            items=[dict(item_code=items[0], current_reading=15, warehouse=warehouse, stock_uom='Nos', uom='Nos')])).insert()
        assert reading.bill_structure_assignment == assignment.name
        reading.submit()
        order_name = frappe.db.get_value('Sales Order Item', {'meter_reading': reading.name}, 'parent')
        order = frappe.get_doc('Sales Order', order_name)
        assert [(row.qty, row.rate) for row in order.items] == [(15, 8), (15, 4)]
        assert order.net_total == 180
        fixed_customer = frappe.get_doc(dict(doctype='Customer', customer_name='Fixed Check ' + suffix, customer_type='Individual')).insert()
        fixed = frappe.get_doc(dict(doctype='Utility Bill Structure', naming_series='UBS-.YYYY.-', fiscal_year=fy,
            company=company, items=[dict(item=items[0], amount=500, discount=10)])).insert()
        fixed.submit()
        fixed_assignment = frappe.get_doc(dict(doctype='Utility Bill Structure Assignment', customer=fixed_customer.name,
            company=company, utility_bill_structure=fixed.name, start_date=date)).insert()
        fixed_assignment.submit()
        fixed_reading = frappe.get_doc(dict(doctype='Meter Reading', customer=fixed_customer.name, company=company,
            currency=currency, price_list=price_list, warehouse=warehouse, date=date,
            )).insert()
        assert fixed_reading.bill_structure_assignment == fixed_assignment.name
        fixed_reading.submit()
        fixed_order = frappe.get_doc('Sales Order', frappe.db.get_value('Sales Order Item', {'meter_reading': fixed_reading.name}, 'parent'))
        assert fixed_order.net_total == 450
        duplicate = frappe.copy_doc(fixed_reading)
        duplicate.insert()
        try:
            duplicate.submit()
        except frappe.ValidationError:
            pass
        else:
            raise AssertionError('Duplicate monthly bill was accepted')
        other_structure = frappe.get_doc(dict(doctype='Utility Bill Structure', naming_series='UBS-.YYYY.-', fiscal_year=fy,
            company=company, items=[dict(item=items[1], calculation_type='Formula', formula='75 + days_in_month * 2')])).insert()
        other_structure.submit()
        from frappe.utils import add_months, add_days
        next_date = add_months(date, 1)
        replacement = frappe.get_doc('Utility Bill Structure Assignment', fixed_assignment.change_structure(other_structure.name, next_date))
        fixed_assignment.reload()
        assert replacement.previous_assignment == fixed_assignment.name
        assert getdate(fixed_assignment.end_date) == getdate(add_days(next_date, -1))
        assert fixed_reading.bill_structure_assignment == fixed_assignment.name
        new_reading = frappe.get_doc(dict(doctype='Meter Reading', customer=fixed_customer.name, company=company,
            currency=currency, price_list=price_list, warehouse=warehouse, date=next_date,
            )).insert()
        assert new_reading.bill_structure_assignment == replacement.name
        new_reading.submit()
        assert new_reading.rates[0].amount >= 131
        return {'assignment_history_preserved': True, 'other_formula_total': new_reading.rates[0].amount, 'metered_total': order.net_total, 'fixed_total': fixed_order.net_total, 'duplicate_blocked': True, 'rolled_back': True}
    finally:
        frappe.db.rollback()


def verify_progressive_sample_order():
    """Check the existing sample bill through Sales Order creation, then roll back."""
    if frappe.local.site != 'utility-billing.localhost':
        frappe.throw('This check is restricted to utility-billing.localhost.')
    try:
        name = frappe.db.get_value('Meter Reading', {'customer': 'Amina Otieno', 'docstatus': 0}, 'name')
        reading = frappe.get_doc('Meter Reading', name)
        reading.items[0].current_reading = 15
        reading.save()
        assert len(reading.rates) == 2
        assert len(reading.calculations) == 8
        reading.submit()
        order_name = frappe.db.get_value('Sales Order Item', {'meter_reading': reading.name}, 'parent')
        order = frappe.get_doc('Sales Order', order_name)
        assert len(order.items) == 2
        assert [(r.qty, r.amount) for r in order.items] == [(1, 140), (1, 70)]
        assert abs(order.net_total - 210) < 0.01, order.net_total
        details = [(row.item_code, row.qty, row.rate, row.amount) for row in order.items]
        assert all(row.item_code in ('Water', 'Sewerage') for row in order.items)
        # Other workflows copying a structure must also omit calculation-only rows.
        from utility_billing.utility_billing.doctype.utility_service_request.utility_service_request import get_utility_bill_structure_details
        exported = get_utility_bill_structure_details('Residential Water and Sewerage')
        assert [row['item_code'] for row in exported['items']] == ['Water', 'Sewerage']
        return dict(total=order.net_total, items=details, calculations=len(reading.calculations), rolled_back=True)
    finally:
        frappe.db.rollback()


def verify_stock_sample_order():
    """Check stock quantities using the existing sample, with every change rolled back."""
    if frappe.local.site != 'utility-billing.localhost':
        frappe.throw('This check is restricted to utility-billing.localhost.')
    try:
        item = frappe.get_doc('Item', 'Water')
        item.is_stock_item = 1
        item.save()
        frappe.clear_document_cache('Item', 'Water')
        name = frappe.db.get_value('Meter Reading', {'customer': 'Amina Otieno', 'docstatus': 0}, 'name')
        reading = frappe.get_doc('Meter Reading', name)
        reading.items[0].current_reading = 15
        reading.save()
        assert [(r.item_code, r.qty, r.rate) for r in reading.rates] == [('Water', 10, 10), ('Water', 5, 8), ('Sewerage', 1, 70)]
        reading.submit()
        order = frappe.get_doc('Sales Order', frappe.db.get_value('Sales Order Item', {'meter_reading': reading.name}, 'parent'))
        assert [(r.item_code, r.qty, r.amount) for r in order.items] == [('Water', 10, 100), ('Water', 5, 40), ('Sewerage', 1, 70)]
        assert order.net_total == 210
        order.submit()
        from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note
        delivery = make_delivery_note(order.name)
        water_rows = [r for r in delivery.items if r.item_code == 'Water']
        assert sum(r.qty for r in water_rows) == 15
        assert sum(r.stock_qty for r in water_rows) == 15
        return dict(stock_quantity=sum(r.stock_qty for r in water_rows), water_amount=140,
                    total=order.net_total, delivery_submitted=False, rolled_back=True)
    finally:
        frappe.db.rollback()
        frappe.clear_document_cache('Item', 'Water')
