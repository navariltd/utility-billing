# Copyright (c) 2025, Navari Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _, scrub
from frappe.utils import cint, flt, getdate, nowdate
from erpnext.accounts.utils import get_currency_precision
from collections import defaultdict

def execute(filters=None):
    return PropertyBillingOverview(filters).run()

class PropertyBillingOverview:
    def __init__(self, filters=None):
        self.filters = frappe._dict(filters or {})
        self.filters.report_date = getdate(self.filters.report_date or nowdate())
        self.currency_precision = get_currency_precision() or 2
        self.data = []
        self.columns = []
        self.bill_item_mapping = {}
        self.monthly_rates = {}
        self.start_date = self.filters.get("report_date") or nowdate()

    def run(self):
        self.get_bill_types()
        self.get_columns()
        self.get_property_data()
        if not self.properties:
            return self.columns, self.data, None, None, None
        self.build_bill_item_mapping()
        self.get_monthly_rates()
        self.get_billing_data()
        self.process_data()
        return self.columns, self.data, None, None, None

    def get_bill_types(self):
        self.bill_types = frappe.get_all("Utility Bill Item Type",
            fields=["name", "description"],
            order_by="name")

    def build_bill_item_mapping(self):
        bill_structure_names = list(set([p.utility_bill_structure for p in self.properties if p.utility_bill_structure]))
        if not bill_structure_names:
            return
        ubsi = frappe.qb.DocType("Utility Bill Structure Item")
        bill_structure_items = (
            frappe.qb.from_(ubsi)
            .select(
                ubsi.item,
                ubsi.bill_type,
                ubsi.parent.as_("utility_bill_structure")
            )
            .where(ubsi.parent.isin(bill_structure_names))
            .run(as_dict=True))
        for item in bill_structure_items:
            if item.utility_bill_structure not in self.bill_item_mapping:
                self.bill_item_mapping[item.utility_bill_structure] = {}
            self.bill_item_mapping[item.utility_bill_structure][item.item] = item.bill_type

    def get_monthly_rates(self):
        bill_structure_names = list(set([p.utility_bill_structure for p in self.properties if p.utility_bill_structure]))
        if not bill_structure_names:
            return
        ubsi = frappe.qb.DocType("Utility Bill Structure Item")
        rate_items = (
            frappe.qb.from_(ubsi)
            .select(
                ubsi.item,
                ubsi.bill_type,
                ubsi.total.as_("monthly_rate"),
                ubsi.parent.as_("utility_bill_structure")
            )
            .where(ubsi.parent.isin(bill_structure_names))
            .run(as_dict=True))
        for item in rate_items:
            key = (item.utility_bill_structure, item.item)
            self.monthly_rates[key] = item.monthly_rate

    def get_property_data(self):
        up = frappe.qb.DocType("Utility Property")
        cpi = frappe.qb.DocType("Contract Utility Property Item")
        usr = frappe.qb.DocType("Utility Service Request")
        cust = frappe.qb.DocType("Customer")
        bar = frappe.qb.DocType("Billing Adjustment Rule")
        query = (
            frappe.qb.from_(up)
            .join(cpi).on(cpi.utility_property == up.name)
            .join(usr).on(usr.name == cpi.parent)
            .left_join(cust).on(cust.name == usr.customer)
            .left_join(bar).on(bar.name == cpi.adjustment_rule)
            .select(
                up.name.as_("property"),
                up.property_name,
                up.house_no,
                up.unit_type,
                up.unit_number,
                up.bedrooms,
                up.floor_level,
                up.bathrooms,
                up.unit_size,
                usr.customer,
                usr.name.as_("service_request"),
                usr.utility_bill_structure,
                cust.customer_name,
                cust.mobile_no.as_("contact_number"),
                cust.email_id,
                cpi.start_date,
                cpi.end_date,
                cpi.adjustment_rule,
                bar.frequency.as_("billing_frequency")
            )
            .where(usr.docstatus == 1)
            .where((cpi.end_date.isnull()) | (cpi.end_date >= self.filters.report_date))
            .where(cpi.start_date <= self.filters.report_date)
            .where(usr.company == self.filters.company)
        )
        if self.filters.get("property"):
            query = query.where(up.name == self.filters.property)
        if self.filters.get("customer"):
            query = query.where(usr.customer == self.filters.customer)
        query = query.orderby(up.property_name, up.unit_number)
        self.properties = query.run(as_dict=True)

    def get_billing_data(self):
        property_list = [p.property for p in self.properties]
        customer_list = [p.customer for p in self.properties if p.customer]
        self.billing_data = defaultdict(lambda: {
            "invoiced": 0, "paid": 0, "outstanding": 0, "ordered": 0, "advance": 0,
            "bill_type_invoiced": defaultdict(float),
            "bill_type_paid": defaultdict(float),
            "bill_type_outstanding": defaultdict(float),
            "bill_type_ordered": defaultdict(float),
            "bill_type_advance": defaultdict(float),
            "bill_type_rate": defaultdict(float),
            "opening_outstanding": 0
        })
        if not property_list or not customer_list:
            return

        self.process_opening_invoices(property_list, customer_list)
        self.process_regular_invoices(property_list, customer_list)
        self.process_sales_orders(property_list, customer_list)

    def process_opening_invoices(self, property_list, customer_list):
        """Process opening invoices separately"""
        si = frappe.qb.DocType("Sales Invoice")
        sii = frappe.qb.DocType("Sales Invoice Item")
        
        opening_invoices = (
            frappe.qb.from_(si)
            .join(sii).on(sii.parent == si.name)
            .select(
                si.name.as_("invoice"),
                si.customer,
                si.posting_date,
                si.grand_total,
                si.base_paid_amount,
                si.outstanding_amount,
                sii.utility_property,
                si.utility_service_request,
                sii.item_code,
                sii.base_amount,
            )
            .where(si.docstatus == 1)
            .where(si.customer.isin(customer_list))
            .where(sii.utility_property.isin(property_list))
            .where(sii.item_name == "Opening Invoice Item")
            .where(si.posting_date <= getdate(self.start_date))
            .run(as_dict=True))
        
        for inv_item in opening_invoices:
            property_key = (inv_item.utility_property, inv_item.customer)
                
            outstanding_amount = flt(inv_item.outstanding_amount, self.currency_precision)
            
            self.billing_data[property_key]["opening_outstanding"] += outstanding_amount

    def process_regular_invoices(self, property_list, customer_list):
        """Process regular invoices (non-opening)"""
        si = frappe.qb.DocType("Sales Invoice")
        sii = frappe.qb.DocType("Sales Invoice Item")
        
        regular_invoices = (
            frappe.qb.from_(si)
            .join(sii).on(sii.parent == si.name)
            .select(
                si.name.as_("invoice"),
                si.customer,
                si.posting_date,
                si.grand_total,
                si.outstanding_amount,
                si.status,
                sii.utility_property,
                si.utility_service_request,
                sii.item_code,
                sii.base_amount,
            )
            .where(si.docstatus == 1)
            .where(si.customer.isin(customer_list))
            .where(sii.utility_property.isin(property_list))
            .where(sii.item_name != "Opening Invoice Item")
            .where(si.posting_date <= self.filters.report_date)
            .run(as_dict=True))
        
        invoices_by_id = defaultdict(list)
        for item in regular_invoices:
            invoices_by_id[item.invoice].append(item)
        
        for invoice_name, items in invoices_by_id.items():
            if not items:
                continue
                
            invoice = items[0]
            invoice_total = flt(invoice.grand_total, self.currency_precision)
            paid_amount = flt(invoice.grand_total - invoice.outstanding_amount, self.currency_precision)
            outstanding_amount = flt(invoice.outstanding_amount, self.currency_precision)
            
            paid_ratio = paid_amount / invoice_total if invoice_total else 0
            
            for item in items:
                property_key = (item.utility_property, item.customer)
                bill_type = self.get_bill_type_for_item(item.utility_service_request, item.item_code)
                if not bill_type:
                    continue
                    
                item_amount = flt(item.base_amount, self.currency_precision)
                proportion = item_amount / invoice_total if invoice_total else 0
                
                item_paid = item_amount * paid_ratio
                item_outstanding = item_amount - item_paid
                
                self.billing_data[property_key]["invoiced"] += item_amount
                self.billing_data[property_key]["bill_type_invoiced"][bill_type] += item_amount
                self.billing_data[property_key]["paid"] += item_paid
                self.billing_data[property_key]["bill_type_paid"][bill_type] += item_paid
                self.billing_data[property_key]["outstanding"] += item_outstanding
                self.billing_data[property_key]["bill_type_outstanding"][bill_type] += item_outstanding
                
                if getdate(item.posting_date) < getdate(self.start_date):
                    self.billing_data[property_key]["opening_outstanding"] += item_outstanding

    def process_sales_orders(self, property_list, customer_list):
        """Process sales orders that don't have matching invoices"""
        so = frappe.qb.DocType("Sales Order")
        soi = frappe.qb.DocType("Sales Order Item")
        
        all_orders = (
            frappe.qb.from_(soi)
            .join(so).on(soi.parent == so.name)
            .select(
                so.name.as_("order"),
                so.customer,
                so.transaction_date,
                so.utility_service_request,
                soi.utility_property,
                soi.item_code,
                soi.base_amount,
                soi.delivered_qty,
                soi.qty
            )
            .where(so.docstatus == 1)
            .where(so.customer.isin(customer_list))
            .where(soi.utility_property.isin(property_list))
            .where(so.transaction_date <= self.filters.report_date)
            .where(so.status.notin(['Cancelled', 'Closed']))
            .run(as_dict=True))
        
        si = frappe.qb.DocType("Sales Invoice")
        sii = frappe.qb.DocType("Sales Invoice Item")
        sinv = frappe.qb.DocType("Sales Invoice Item")
        
        invoiced_items = (
            frappe.qb.from_(sii)
            .join(si).on(sii.parent == si.name)
            .select(
                sii.so_detail,
                sii.qty
            )
            .where(si.docstatus == 1)
            .where(si.customer.isin(customer_list))
            .where(sii.utility_property.isin(property_list))
            .where(si.posting_date <= self.filters.report_date)
            .run(as_dict=True))
        
        so_item_invoiced = defaultdict(float)
        for item in invoiced_items:
            if item.so_detail:
                so_item_invoiced[item.so_detail] += item.qty
        
        for order in all_orders:
            if order.name in so_item_invoiced and so_item_invoiced[order.name] >= order.qty:
                continue
                
            property_key = (order.utility_property, order.customer)
            bill_type = self.get_bill_type_for_item(order.utility_service_request, order.item_code)
            if not bill_type:
                continue
                
            item_amount = flt(order.base_amount, self.currency_precision)
            self.billing_data[property_key]["ordered"] += item_amount
            self.billing_data[property_key]["bill_type_ordered"][bill_type] += item_amount

    def get_bill_type_for_item(self, service_request, item_code):
        if not service_request or not item_code:
            return None
        bill_structure = frappe.db.get_value("Utility Service Request", service_request, "utility_bill_structure")
        if bill_structure in self.bill_item_mapping:
            return self.bill_item_mapping[bill_structure].get(item_code)
        return None

    def process_data(self):
        for prop in self.properties:
            property_key = (prop.property, prop.customer)
            billing_info = self.billing_data[property_key]
            row = {
                "property": prop.property,
                "property_name": prop.property_name,
                "house_no": prop.house_no,
                "unit_type": prop.unit_type,
                "unit_number": prop.unit_number,
                "bedrooms": prop.bedrooms,
                "floor_level": prop.floor_level,
                "bathrooms": prop.bathrooms,
                "unit_size": prop.unit_size,
                "customer": prop.customer,
                "customer_name": prop.customer_name,
                "contact_number": prop.contact_number,
                "email_id": prop.email_id,
                "start_date": prop.start_date,
                "end_date": prop.end_date,
                "billing_frequency": prop.billing_frequency,
                "opening_arrears": billing_info.get("opening_outstanding", 0),
                "total_invoiced": billing_info.get("invoiced", 0),
                "total_paid": billing_info.get("paid", 0),
                "total_outstanding": billing_info.get("outstanding", 0),
                "total_ordered": billing_info.get("ordered", 0),
                "currency": frappe.get_cached_value('Company', self.filters.company, 'default_currency')
            }
            for bt in self.bill_types:
                bill_type_name = scrub(bt.name)
                rate_value = 0
                bill_structure = prop.utility_bill_structure
                if bill_structure in self.bill_item_mapping:
                    items_for_bill_type = [item_code for item_code, b_type in self.bill_item_mapping[bill_structure].items() if b_type == bt.name]
                    if items_for_bill_type:
                        item_code = items_for_bill_type[0]
                        rate_key = (bill_structure, item_code)
                        rate_value = self.monthly_rates.get(rate_key, 0)
                row[f"{bill_type_name}_rate"] = rate_value
                row[f"{bill_type_name}_invoiced"] = billing_info["bill_type_invoiced"].get(bt.name, 0)
                row[f"{bill_type_name}_paid"] = billing_info["bill_type_paid"].get(bt.name, 0)
                row[f"{bill_type_name}_outstanding"] = billing_info["bill_type_outstanding"].get(bt.name, 0)
                row[f"{bill_type_name}_ordered"] = billing_info["bill_type_ordered"].get(bt.name, 0)

            self.data.append(row)

    def get_conditions(self):
        conditions = ""
        if self.filters.get("property"):
            conditions += " AND up.name = %(property)s"
        if self.filters.get("customer"):
            conditions += " AND usr.customer = %(customer)s"
        return conditions

    def get_columns(self):
        self.columns = []
        self.columns.extend([
            { "label": _("Property"), "fieldname": "property", "fieldtype": "Link", "options": "Utility Property", "width": 150 },
            { "label": _("Customer"), "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 150 },
            { "label": _("Customer Contact"), "fieldname": "contact_number", "fieldtype": "Data", "width": 150 },
            { "label": _("Unit Size"), "fieldname": "unit_size", "fieldtype": "Float", "width": 120 },
        ])
        if self.filters.get("show_property_fields"):
            self.columns.extend([
                { "label": _("Unit Type"), "fieldname": "unit_type", "fieldtype": "Data", "width": 100 },
                { "label": _("Unit Number"), "fieldname": "unit_number", "fieldtype": "Data", "width": 100 },
                { "label": _("Bedrooms"), "fieldname": "bedrooms", "fieldtype": "Int", "width": 80 },
                { "label": _("Floor Level"), "fieldname": "floor_level", "fieldtype": "Data", "width": 80 },
                { "label": _("Bathrooms"), "fieldname": "bathrooms", "fieldtype": "Int", "width": 80 },
                { "label": _("House No"), "fieldname": "house_no", "fieldtype": "Data", "width": 80 },
            ])
        self.columns.extend([
            { "label": _("Lease Start"), "fieldname": "start_date", "fieldtype": "Date", "width": 150 },
            { "label": _("Lease End"), "fieldname": "end_date", "fieldtype": "Date", "width": 150 },
            { "label": _("Opening Arrears"), "fieldname": "opening_arrears", "fieldtype": "Currency", "options": "currency", "width": 150 }
        ])
        for bt in self.bill_types:
            bill_type_name = scrub(bt.name)
            self.columns.extend([
                { "label": _(f"{bt.name} Rate"), "fieldname": f"{bill_type_name}_rate", "fieldtype": "Currency", "options": "currency", "width": 120 },
                { "label": _(f"{bt.name} Invoiced"), "fieldname": f"{bill_type_name}_invoiced", "fieldtype": "Currency", "options": "currency", "width": 120 },
                { "label": _(f"{bt.name} Ordered"), "fieldname": f"{bill_type_name}_ordered", "fieldtype": "Currency", "options": "currency", "width": 120 }
            ])
        if self.filters.get("show_totals"):
            self.columns.extend([
                { "label": _("Total Invoiced"), "fieldname": "total_invoiced", "fieldtype": "Currency", "options": "currency", "width": 150 },
                { "label": _("Total Paid"), "fieldname": "total_paid", "fieldtype": "Currency", "options": "currency", "width": 150 },
                { "label": _("Total Outstanding"), "fieldname": "total_outstanding", "fieldtype": "Currency", "options": "currency", "width": 150 },
                { "label": _("Total Ordered"), "fieldname": "total_ordered", "fieldtype": "Currency", "options": "currency", "width": 150 },
            ])