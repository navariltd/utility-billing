"""Small, realistic billing examples. Explicit invocation only; never a migration patch.

Uses normal document creation, with no ERPNext test runner or test fixtures.
"""
import frappe
from frappe.utils import add_days, add_months, get_first_day, getdate, nowdate


def ensure(doctype, name, values, submit=False):
    if frappe.db.exists(doctype, name):
        doc = frappe.get_doc(doctype, name)
    else:
        doc = frappe.get_doc(dict(doctype=doctype, **values)).insert(set_name=name)
    if submit and doc.docstatus == 0:
        doc.submit()
    return doc


def execute():
    if frappe.local.site != 'utility-billing.localhost':
        frappe.throw('This sample setup is restricted to utility-billing.localhost.')
    # Minimal normal setup records needed after reinstall; these are not test fixtures.
    ensure('Warehouse Type', 'Transit', dict(description='Goods in transit'))
    ensure('Item Group', 'All Item Groups', dict(item_group_name='All Item Groups', is_group=1))
    ensure('Customer Group', 'All Customer Groups', dict(customer_group_name='All Customer Groups', is_group=1))
    ensure('Territory', 'All Territories', dict(territory_name='All Territories', is_group=1))
    date = nowdate()
    month_start = get_first_day(date)
    year = getdate(date).year
    fiscal_year = frappe.db.get_value('Fiscal Year', {'year_start_date': ('<=', date), 'year_end_date': ('>=', date)}, 'name')
    if not fiscal_year:
        fiscal_year = ensure('Fiscal Year', str(year), dict(year=str(year), year_start_date=f'{year}-01-01', year_end_date=f'{year}-12-31')).name
    company = ensure('Company', 'Mwangaza Water Services', dict(company_name='Mwangaza Water Services',
        abbr='MWS', country='Kenya', default_currency='KES',
        create_chart_of_accounts_based_on='Standard Template', chart_of_accounts='Standard')).name
    warehouse = frappe.db.get_value('Warehouse', {'company': company, 'is_group': 0}, 'name')
    if not warehouse:
        warehouse = ensure('Warehouse', 'Main Store - MWS', dict(warehouse_name='Main Store', company=company)).name
    price_list = ensure('Price List', 'Water Tariffs', dict(price_list_name='Water Tariffs', currency='KES', selling=1, enabled=1)).name
    ensure('Item Group', 'Utility Services', dict(item_group_name='Utility Services', parent_item_group='All Item Groups', is_group=0, is_utility_item_group=1))
    ensure('UOM', 'Cubic Meter', dict(uom_name='Cubic Meter', must_be_whole_number=0))
    ensure('UOM', 'Unit', dict(uom_name='Unit', must_be_whole_number=1))
    for name in ('Water', 'Sewerage', 'Service Charge'):
        ensure('Item', name, dict(item_code=name, item_name=name, item_group='Utility Services',
            stock_uom='Unit' if name == 'Service Charge' else 'Cubic Meter', is_stock_item=0,
            is_sales_item=1, is_utility_item=1))

    specifications = sample_structures()
    for name, values in specifications.items():
        ensure('Utility Bill Structure', name, dict(naming_series='UBS-.YYYY.-', fiscal_year=fiscal_year, company=company, **values), submit=True)

    def customer(name):
        return ensure('Customer', name, dict(customer_name=name, customer_type='Individual',
            customer_group='Individual', territory='Kenya', default_price_list=price_list)).name

    def assignment(person, structure, start, end=None, previous=None):
        existing = frappe.db.get_value('Utility Bill Structure Assignment',
            dict(customer=person, company=company, utility_bill_structure=structure, start_date=start, docstatus=1), 'name')
        if existing:
            return frappe.get_doc('Utility Bill Structure Assignment', existing)
        doc = frappe.get_doc(dict(doctype='Utility Bill Structure Assignment', customer=person, company=company,
            utility_bill_structure=structure, start_date=start, end_date=end, previous_assignment=previous)).insert()
        doc.submit()
        return doc

    ensure('Customer Group', 'Individual', dict(customer_group_name='Individual', parent_customer_group='All Customer Groups', is_group=0))
    ensure('Territory', 'Kenya', dict(territory_name='Kenya', parent_territory='All Territories', is_group=0))
    examples = []
    for person, structure, total in [
        ('Amina Otieno', 'Residential Water and Sewerage', 210),
        ('James Mwangi', 'Residential Water Only', 140),
        ('Grace Wanjiku', 'Water with Service Charge', 190),
        ('Peter Kamau', 'Fixed Monthly Water and Sewerage', 700),
    ]:
        person = customer(person)
        assigned = assignment(person, structure, month_start)
        existing = frappe.db.get_value('Meter Reading', dict(customer=person, company=company, date=date, docstatus=0), 'name')
        if existing:
            reading = frappe.get_doc('Meter Reading', existing)
        else:
            rows = [] if structure == 'Fixed Monthly Water and Sewerage' else [dict(item_code='Water', current_reading=15,
                warehouse=warehouse, stock_uom='Cubic Meter', uom='Cubic Meter')]
            reading = frappe.get_doc(dict(doctype='Meter Reading', customer=person, company=company, date=date,
                currency='KES', price_list=price_list, warehouse=warehouse, items=rows)).insert()
        actual = sum(row.amount for row in reading.rates)
        if actual != total:
            frappe.throw(f'{person}: expected {total}, got {actual}.')
        examples.append(dict(customer=person, structure=structure, assignment=assigned.name, draft_bill=reading.name, total=actual))

    person = customer('Faith Achieng')
    old = assignment(person, 'Residential Water Only', get_first_day(add_months(date, -1)), add_days(month_start, -1))
    new = assignment(person, 'Residential Water and Sewerage', month_start, previous=old.name)
    selling_settings = frappe.get_single('Selling Settings')
    if not selling_settings.allow_multiple_items:
        selling_settings.allow_multiple_items = 1
        selling_settings.save()
    defaults = frappe.get_single('Global Defaults')
    defaults.update(dict(default_company=company, default_currency='KES', country='Kenya'))
    defaults.save()
    frappe.defaults.set_user_default('Company', company, user='Administrator')
    frappe.defaults.set_user_default('Currency', 'KES', user='Administrator')
    frappe.db.set_default('fiscal_year', fiscal_year)
    frappe.db.set_single_value('Utility Billing Settings', 'sales_order_creation_state', 'Draft')
    # Keep the reset development site accessible without the setup wizard.
    for app in ('frappe', 'erpnext'):
        frappe.db.set_value('Installed Application', {'app_name': app}, 'is_setup_complete', 1)
    frappe.db.set_single_value('System Settings', {'setup_complete': 1, 'enable_onboarding': 0, 'time_zone': 'Africa/Nairobi'})
    frappe.db.set_default('setup_complete', 1)
    frappe.db.set_default('desktop:home_page', 'workspace')
    meters = setup_meters()
    frappe.clear_cache()
    return dict(meters=meters, company=company, currency='KES', date=date, examples=examples,
        history=dict(customer=person, previous=old.name, current=new.name),
        test_companies=frappe.get_all('Company', filters={'name': ('like', '_Test%')}, pluck='name'))


def setup_meters():
    """Attach one commissioned meter to each sample consumption customer."""
    if frappe.local.site != 'utility-billing.localhost':
        frappe.throw('This sample setup is restricted to utility-billing.localhost.')
    from utility_billing.utility_billing.utils.request_link import check_meters_of_customer
    from utility_billing.utility_billing.utils.utils import get_serial_numbers_from_warranty_claims

    company = 'Mwangaza Water Services'
    if not frappe.db.exists('Company', company):
        frappe.throw('Create the sample company and customers before assigning meters.')
    stock_settings = frappe.get_single('Stock Settings')
    if not stock_settings.enable_serial_and_batch_no_for_item:
        stock_settings.enable_serial_and_batch_no_for_item = 1
        stock_settings.save()
    ensure('Item', 'Water Meter', dict(item_code='Water Meter', item_name='Water Meter',
        item_group='Utility Services', stock_uom='Unit', is_stock_item=1,
        has_serial_no=1, is_sales_item=1, is_utility_item=0))
    result = []
    for person, meter in [('Amina Otieno', 'WM-1001'), ('James Mwangi', 'WM-1002'),
                          ('Grace Wanjiku', 'WM-1003'), ('Faith Achieng', 'WM-1004')]:
        if not frappe.db.exists('Customer', person):
            frappe.throw(f'Customer {person} does not exist.')
        serial = ensure('Serial No', meter, dict(serial_no=meter, item_code='Water Meter',
            company=company, customer=person, status='Delivered'))
        if serial.customer != person or serial.item_code != 'Water Meter' or serial.company != company:
            frappe.throw(f'Meter {meter} is already registered with different details.')
        claim_name = frappe.db.get_value('Warranty Claim', dict(customer=person, serial_no=meter, status='Closed'), 'name')
        if not claim_name:
            installed_on = get_first_day(add_months(nowdate(), -1)) if person == 'Faith Achieng' else get_first_day(nowdate())
            claim = frappe.get_doc(dict(doctype='Warranty Claim', naming_series='SER-WRN-.YYYY.-',
                customer=person, company=company, serial_no=meter, item_code='Water Meter',
                complaint_date=installed_on, complaint='Water meter installation and commissioning',
                status='Closed', resolved_by='Administrator',
                resolution_details='Meter installed, connected and commissioned for water consumption billing.')).insert()
            claim_name = claim.name
        updated = []
        for name in frappe.get_all('Meter Reading', filters=dict(customer=person, company=company, docstatus=0), pluck='name'):
            reading = frappe.get_doc('Meter Reading', name)
            before = sum(row.amount for row in reading.rates)
            changed = False
            for row in reading.items:
                if row.item_code == 'Water' and not row.meter_number:
                    row.meter_number = meter
                    changed = True
            if changed:
                reading.save()
                if sum(row.amount for row in reading.rates) != before:
                    frappe.throw(f'Adding meter {meter} unexpectedly changed the charges on {name}.')
                updated.append(name)
            check_meters_of_customer(reading)
        selectable = get_serial_numbers_from_warranty_claims(person)
        if meter not in selectable:
            frappe.throw(f'Meter {meter} is not selectable for {person}.')
        result.append(dict(customer=person, meter=meter, installation=claim_name, updated_drafts=updated))
    frappe.db.commit()
    return result


def progressive_rows(item, prefix, rates, total_abbreviation):
    """First ten units, next ten units, then all remaining consumption."""
    amounts = [
        f'consumption * {rates[0]} if consumption <= 10 else 10 * {rates[0]}',
        f'(consumption - 10) * {rates[1]} if consumption <= 20 else 10 * {rates[1]}',
        f'(consumption - 20) * {rates[2]}',
    ]
    conditions = ['consumption > 0', 'consumption > 10', 'consumption > 20']
    labels = ['first 10 units', 'next 10 units', 'above 20 units']
    rows = [dict(row_type='Calculation Only', label=f'{item}: {label}', abbreviation=f'{prefix}{index}',
        calculation_type='Formula', condition=condition, formula=amount)
        for index, (label, condition, amount) in enumerate(zip(labels, conditions, amounts), 1)]
    rows.append(dict(row_type='Billable Item', item=item, abbreviation=total_abbreviation,
        calculation_type='Formula', formula=' + '.join(f'{prefix}{i}' for i in range(1, 4)), stock_quantity_sources=', '.join(f'{prefix}{i}' for i in range(1, 4))))
    return rows


def sample_structures():
    water = progressive_rows('Water', 'W', (10, 8, 6), 'water_total')
    sewer = progressive_rows('Sewerage', 'S', (5, 4, 3), 'sewerage_total')
    return {
        'Residential Water and Sewerage': dict(metered_billing=1, water_item='Water', items=water + sewer, bands=[]),
        'Residential Water Only': dict(metered_billing=1, water_item='Water', items=water, bands=[]),
        'Water with Service Charge': dict(metered_billing=1, water_item='Water', items=water + [
            dict(row_type='Billable Item', item='Service Charge', calculation_type='Formula', formula='water_total * 0.2 if water_total * 0.2 >= 50 else 50')], bands=[]),
        'Fixed Monthly Water and Sewerage': dict(items=[dict(item='Water', amount=500), dict(item='Sewerage', amount=200)], bands=[]),
    }
