# Copyright (c) 2025, Navari Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _, scrub
from frappe.utils import flt, getdate
from erpnext.accounts.utils import get_currency_precision, get_balance_on
from collections import defaultdict
from frappe.query_builder import functions as fn

def execute(filters=None):
    return PropertyBillingOverview(filters).run()

class PropertyBillingOverview:
    def __init__(self, filters=None):
        self.filters = frappe._dict(filters or {})
        self.validate_filters()
        self.currency_precision = get_currency_precision() or 2
        self.data = []
        self.columns = []
        self.property_contract_map = {}
        self.bill_item_mapping = {}
        self.monthly_rates = {}
        self.bill_types = []
        self.customer_totals = {}

    def validate_filters(self):
        if not self.filters.get("company"):
            frappe.throw(_("Company is required"))
        if not self.filters.get("from_date") or not self.filters.get("to_date"):
            frappe.throw(_("Date range is required"))
            
        self.filters.from_date = getdate(self.filters.from_date)
        self.filters.to_date = getdate(self.filters.to_date)
        
        if self.filters.from_date > self.filters.to_date:
            frappe.throw(_("From Date cannot be after To Date"))

    def run(self):
        self.get_bill_types()
        self.get_columns() 
        self.get_contract_data()
        
        if not self.contracts:
            return self.columns, self.data
            
        self.build_bill_item_mapping()
        self.get_monthly_rates()
        self.get_billing_data()
        self.process_data()
        
        return self.columns, self.data

    def get_bill_types(self):
        self.bill_types = frappe.get_all("Item Group",
            filters={"is_utility_item_group": 1},
            fields=["name"],
            order_by="name")

    def get_contract_data(self):
        contract = frappe.qb.DocType("Contract")
        contract_property = frappe.qb.DocType("Contract Utility Property Item")
        property_doc = frappe.qb.DocType("Utility Property")
        service_request = frappe.qb.DocType("Utility Service Request")
        customer = frappe.qb.DocType("Customer")
        adjustment_rule = frappe.qb.DocType("Billing Adjustment Rule")

        query = (
            frappe.qb.from_(contract)
            .join(contract_property).on(contract_property.parent == contract.name)
            .join(property_doc).on(property_doc.name == contract_property.utility_property)
            .left_join(service_request).on(service_request.name == contract.utility_service_request)
            .left_join(customer).on(customer.name == contract.party_name)
            .left_join(adjustment_rule).on(adjustment_rule.name == contract_property.adjustment_rule)
            .select(
                contract.name.as_("contract"),
                contract.party_name.as_("customer"),
                contract.utility_service_request,
                service_request.utility_bill_structure,
                customer.customer_name,
                customer.mobile_no.as_("contact_number"),
                customer.email_id,
                contract_property.utility_property.as_("property"),
                property_doc.property_name,
                property_doc.house_no,
                property_doc.unit_type,
                property_doc.unit_number,
                property_doc.bedrooms,
                property_doc.floor_level,
                property_doc.bathrooms,
                property_doc.unit_size,
                contract_property.start_date,
                contract_property.end_date,
                contract_property.adjustment_rule,
                adjustment_rule.frequency.as_("billing_frequency")
            )
            .where(contract.docstatus == 1)
            .where(service_request.company == self.filters.company)
        )

        if self.filters.get("property"):
            query = query.where(contract_property.utility_property == self.filters.property)
        if self.filters.get("customer"):
            query = query.where(contract.party_name == self.filters.customer)

        self.contracts = query.orderby(contract.party_name, property_doc.property_name, property_doc.unit_number).run(as_dict=True)
        
        for contract in self.contracts:
            self.property_contract_map[contract.property] = contract

    def build_bill_item_mapping(self):
        bill_structure_names = list(set(c.utility_bill_structure for c in self.contracts if c.utility_bill_structure))
        if not bill_structure_names:
            return
            
        ubsi = frappe.qb.DocType("Utility Bill Structure Item")
        item = frappe.qb.DocType("Item")
        
        bill_structure_items = (
            frappe.qb.from_(ubsi)
            .join(item).on(item.name == ubsi.item)
            .select(
                ubsi.item,
                item.item_group,
                ubsi.parent.as_("utility_bill_structure")
            )
            .where(ubsi.parent.isin(bill_structure_names))
            .run(as_dict=True))
            
        for item in bill_structure_items:
            self.bill_item_mapping.setdefault(item.utility_bill_structure, {})[item.item] = item.item_group

    def get_monthly_rates(self):
        bill_structure_names = list(set(c.utility_bill_structure for c in self.contracts if c.utility_bill_structure))
        if not bill_structure_names:
            return
            
        ubsi = frappe.qb.DocType("Utility Bill Structure Item")
        rate_items = (
            frappe.qb.from_(ubsi)
            .select(
                ubsi.item,
                ubsi.total.as_("monthly_rate"),
                ubsi.parent.as_("utility_bill_structure")
            )
            .where(ubsi.parent.isin(bill_structure_names))
            .run(as_dict=True))
            
        self.monthly_rates = {(item.utility_bill_structure, item.item): item.monthly_rate for item in rate_items}

    def get_billing_data(self):
        property_list = [c.property for c in self.contracts]
        customer_list = [c.customer for c in self.contracts if c.customer]

        self.billing_data = defaultdict(lambda: {
            "invoiced": 0,
            "paid": 0,
            "outstanding": 0,
            "ordered": 0,
            "opening_outstanding": 0,
            "current_outstanding": 0,
            "bill_type_invoiced": defaultdict(float),
            "bill_type_paid": defaultdict(float),
            "bill_type_outstanding": defaultdict(float),
            "bill_type_ordered": defaultdict(float),
            "bill_type_rate": defaultdict(float)
        })

        if not property_list or not customer_list:
            return

        self.get_opening_balances(customer_list)
        self.get_paid_in_period(customer_list)
        self.get_current_outstanding(customer_list)
        self.get_invoices(property_list, customer_list)
        self.get_sales_orders(property_list, customer_list)

    def get_opening_balances(self, customer_list):
        for customer in customer_list:
            opening_balance = get_balance_on(
                party_type="Customer",
                party=customer,
                date=self.filters.from_date,
                company=self.filters.company
            )
            
            for contract in (c for c in self.contracts if c.customer == customer):
                self.billing_data[(contract.property, contract.customer)]["opening_outstanding"] = opening_balance

    def get_invoices(self, property_list, customer_list):
        si = frappe.qb.DocType("Sales Invoice")
        sii = frappe.qb.DocType("Sales Invoice Item")
        
        invoices = (
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
            .where(si.posting_date.between(self.filters.from_date, self.filters.to_date))
            .run(as_dict=True))
            
        for invoice in invoices:
            property_key = (invoice.utility_property, invoice.customer)
            bill_type = self.get_bill_type_for_item(invoice.utility_service_request, invoice.item_code)
            if not bill_type:
                continue
                
        # First calculate customer totals
            item_amount = flt(invoice.base_amount, self.currency_precision)
            
            self.update_billing_data(property_key, bill_type, item_amount)

    def update_billing_data(self, property_key, bill_type, invoiced):
        data = self.billing_data[property_key]
        data["invoiced"] += invoiced
        data["bill_type_invoiced"][bill_type] += invoiced

    def get_sales_orders(self, property_list, customer_list):
        so = frappe.qb.DocType("Sales Order")
        soi = frappe.qb.DocType("Sales Order Item")
        
        orders = (
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
        # First calculate customer totals
                soi.qty
            )
            .where(so.docstatus == 1)
            .where(so.customer.isin(customer_list))
            .where(soi.utility_property.isin(property_list))
            .where(so.transaction_date.between(self.filters.from_date, self.filters.to_date))
            .where(so.status.notin(['Cancelled', 'Closed']))
            .run(as_dict=True))
            
        invoiced_qty = self.get_invoiced_qty_for_orders()
            
        for order in orders:
            if order.name in invoiced_qty and invoiced_qty[order.name] >= order.qty:
                continue
        # First calculate customer totals
                
            property_key = (order.utility_property, order.customer)
            bill_type = self.get_bill_type_for_item(order.utility_service_request, order.item_code)
            if not bill_type:
                continue
                
            item_amount = flt(order.base_amount, self.currency_precision)
            self.billing_data[property_key]["ordered"] += item_amount
            self.billing_data[property_key]["bill_type_ordered"][bill_type] += item_amount

    def get_invoiced_qty_for_orders(self):
        sii = frappe.qb.DocType("Sales Invoice Item")
        result = (
            frappe.qb.from_(sii)
            .select(
                sii.so_detail,
                frappe.qb.terms.Function("SUM", sii.qty).as_("qty")
            )
            .where(sii.docstatus == 1)
            .where(sii.so_detail.isnotnull())
            .groupby(sii.so_detail)
            .run(as_dict=True)
        )
        return {row.so_detail: row.qty for row in result}
    
    def get_bill_type_for_item(self, service_request, item_code):
        if not service_request or not item_code:
            return None
            
        bill_structure = frappe.db.get_value("Utility Service Request", service_request, "utility_bill_structure")
        return self.bill_item_mapping.get(bill_structure, {}).get(item_code)
    
    def get_total_paid_in_period(self, customer, company, from_date, to_date):
        """Get total paid amount for a customer between from_date and to_date using Payment Ledger Entry."""
        ple = frappe.qb.DocType("Payment Ledger Entry")
        acc = frappe.qb.DocType("Account")

        account_type = frappe.get_cached_value("Party Type", "Customer", "account_type")

        query = (
            frappe.qb.from_(ple)
            .inner_join(acc).on(ple.account == acc.name)
            .select(fn.Sum(ple.amount).as_("paid_amount"))
            .where(ple.party_type == "Customer")
            .where(ple.party == customer)
            .where(ple.company == company)
            .where(ple.posting_date.between(from_date, to_date))
            .where(acc.account_type == account_type)
            .where(ple.delinked == 0)                 
            .where(ple.amount < 0)                   
        )

        if invoice_doctypes := frappe.get_hooks("invoice_doctypes"):
            query = query.where(ple.voucher_type.notin(invoice_doctypes))

        result = query.run()
        paid_amount = abs(flt(result[0][0])) if result and result[0][0] else 0

        return paid_amount

    def get_paid_in_period(self, customer_list):
        for customer in customer_list:
            paid_amount = self.get_total_paid_in_period(
                customer=customer,
                company=self.filters.company,
                from_date=self.filters.from_date,
                to_date=self.filters.to_date
            )

            for contract in (c for c in self.contracts if c.customer == customer):
                self.billing_data[(contract.property, contract.customer)]["paid"] = paid_amount

    def get_current_outstanding(self, customer_list):
        for customer in customer_list:
            closing_balance = get_balance_on(
                party_type="Customer",
                party=customer,
                date=self.filters.to_date,
                company=self.filters.company
            )
            for contract in (c for c in self.contracts if c.customer == customer):
                self.billing_data[(contract.property, contract.customer)]["current_outstanding"] = closing_balance

    def process_data(self):
        self.calculate_customer_totals()
        
        current_customer = None
        for contract in self.contracts:
            property_key = (contract.property, contract.customer)
            billing_info = self.billing_data[property_key]
            
            is_first_row_for_customer = (contract.customer != current_customer)
            current_customer = contract.customer
            
            row = {
                "property": contract.property,
                "property_name": contract.property_name,
                "house_no": contract.house_no,
                "unit_type": contract.unit_type,
                "unit_number": contract.unit_number,
                "bedrooms": contract.bedrooms,
                "floor_level": contract.floor_level,
                "bathrooms": contract.bathrooms,
                "unit_size": contract.unit_size,
                "customer": contract.customer,
                "customer_name": contract.customer_name,
                "contact_number": contract.contact_number if is_first_row_for_customer else "",
                "email_id": contract.email_id if is_first_row_for_customer else "",
                "start_date": contract.start_date,
                "end_date": contract.end_date,
                "billing_frequency": contract.billing_frequency,
                "indent": 1 if not is_first_row_for_customer else 0,
                "is_group": 0,
                "parent_customer": contract.customer if not is_first_row_for_customer else "",
                "opening_arrears": billing_info.get("opening_outstanding", 0) if is_first_row_for_customer else "",
                "total_paid": billing_info.get("paid", 0) if is_first_row_for_customer else "",
                "current_outstanding_arrears": billing_info.get("current_outstanding", 0) if is_first_row_for_customer else "",
                "total_invoiced": billing_info.get("invoiced", 0),
                "total_ordered": billing_info.get("ordered", 0),
                "currency": frappe.get_cached_value('Company', self.filters.company, 'default_currency')
            }
            
            self.add_bill_type_data(row, contract, billing_info, is_first_row_for_customer)
            self.data.append(row)
          

    def calculate_customer_totals(self):
        self.customer_totals = defaultdict(lambda: {
            "opening_arrears": 0,
            "total_paid": 0,
            "current_outstanding_arrears": 0,
            "total_invoiced": 0,
            "total_ordered": 0,
            "bill_type_invoiced": defaultdict(float),
            "bill_type_ordered": defaultdict(float)
        })

        for contract in self.contracts:
            property_key = (contract.property, contract.customer)
            billing_info = self.billing_data[property_key]
            
            customer_data = self.customer_totals[contract.customer]
            customer_data["opening_arrears"] = billing_info.get("opening_outstanding", 0)
            customer_data["total_paid"] = billing_info.get("paid", 0)
            customer_data["current_outstanding_arrears"] = billing_info.get("current_outstanding", 0)
            customer_data["total_invoiced"] += billing_info.get("invoiced", 0)
            customer_data["total_ordered"] += billing_info.get("ordered", 0)
            
            for bt in self.bill_types:
                if bt.name in billing_info["bill_type_invoiced"]:
                    customer_data["bill_type_invoiced"][bt.name] += billing_info["bill_type_invoiced"][bt.name]
                if bt.name in billing_info["bill_type_ordered"]:
                    customer_data["bill_type_ordered"][bt.name] += billing_info["bill_type_ordered"][bt.name]


    def create_customer_total_row(self, customer):
        customer_data = self.customer_totals[customer]
        contract = next(c for c in self.contracts if c.customer == customer)
        
        row = {
            "customer": customer,
            "customer_name": contract.customer_name,
            "contact_number": contract.contact_number,
            "email_id": contract.email_id,
            "opening_arrears": customer_data["opening_arrears"],
            "total_paid": customer_data["total_paid"],
            "current_outstanding_arrears": customer_data["current_outstanding_arrears"],
            "total_invoiced": customer_data["total_invoiced"],
            "total_ordered": customer_data["total_ordered"],
            "indent": 0,
            "is_group": 1,
            "currency": frappe.get_cached_value('Company', self.filters.company, 'default_currency')
        }
        
        for bt in self.bill_types:
            bill_type_name = scrub(bt.name)
            row.update({
                f"{bill_type_name}_invoiced": customer_data["bill_type_invoiced"].get(bt.name, 0),
                f"{bill_type_name}_ordered": customer_data["bill_type_ordered"].get(bt.name, 0)
            })
        
        return row

    def add_bill_type_data(self, row, contract, billing_info, is_first_row_for_customer):
        for bt in self.bill_types:
            bill_type_name = scrub(bt.name)
            rate_value = 0
            
            if contract.utility_bill_structure in self.bill_item_mapping:
                items_for_bill_type = [
                    item_code for item_code, item_group in 
                    self.bill_item_mapping[contract.utility_bill_structure].items() 
                    if item_group == bt.name
                ]
                if items_for_bill_type:
                    rate_key = (contract.utility_bill_structure, items_for_bill_type[0])
                    rate_value = self.monthly_rates.get(rate_key, 0)
            
            row.update({
                f"{bill_type_name}_rate": rate_value if is_first_row_for_customer else "",
                f"{bill_type_name}_invoiced": billing_info["bill_type_invoiced"].get(bt.name, 0),
                f"{bill_type_name}_ordered": billing_info["bill_type_ordered"].get(bt.name, 0)
            })

    def get_columns(self):
        base_columns = [
            {"label": _("Customer"), "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 150},
            {"label": _("Contact"), "fieldname": "contact_number", "fieldtype": "Data", "width": 150},
            {"label": _("Property"), "fieldname": "property", "fieldtype": "Link", "options": "Utility Property", "width": 150},
            {"label": _("Unit Size"), "fieldname": "unit_size", "fieldtype": "Float", "width": 150},
            {"label": _("Lease Start"), "fieldname": "start_date", "fieldtype": "Date", "width": 150},
            {"label": _("Lease End"), "fieldname": "end_date", "fieldtype": "Date", "width": 150},
            {"label": _("Opening Arrears"), "fieldname": "opening_arrears", "fieldtype": "Currency", "options": "currency", "width": 150},
            {"label": _("Paid Amount"), "fieldname": "total_paid", "fieldtype": "Currency", "options": "currency", "width": 150},
            {"label": _("Outstanding Arrears"), "fieldname": "current_outstanding_arrears", "fieldtype": "Currency", "options": "currency", "width": 150},
        ]
        
        if self.filters.get("show_property_fields"):
            base_columns.extend([
                {"label": _("Unit Type"), "fieldname": "unit_type", "fieldtype": "Data", "width": 150},
                {"label": _("Unit Number"), "fieldname": "unit_number", "fieldtype": "Data", "width": 150},
                {"label": _("Bedrooms"), "fieldname": "bedrooms", "fieldtype": "Int", "width": 80},
                {"label": _("Floor Level"), "fieldname": "floor_level", "fieldtype": "Data", "width": 80},
                {"label": _("Bathrooms"), "fieldname": "bathrooms", "fieldtype": "Int", "width": 80},
                {"label": _("House No"), "fieldname": "house_no", "fieldtype": "Data", "width": 80},
            ])
        
        for bt in self.bill_types:
            bill_type_name = scrub(bt.name)
            base_columns.append(
                {"label": _(f"{bt.name} Rate (Monthly)"), "fieldname": f"{bill_type_name}_rate", "fieldtype": "Currency", "options": "currency", "width": 150}
            )
        
        for bt in self.bill_types:
            bill_type_name = scrub(bt.name)
            base_columns.append(
                {"label": _(f"{bt.name} Ordered Amount"), "fieldname": f"{bill_type_name}_ordered", "fieldtype": "Currency", "options": "currency", "width": 150}
            )
            
        for bt in self.bill_types:
            bill_type_name = scrub(bt.name)
            base_columns.append(
                {"label": _(f"{bt.name} Invoiced Amount"), "fieldname": f"{bill_type_name}_invoiced", "fieldtype": "Currency", "options": "currency", "width": 150}
            )
        
        if self.filters.get("show_totals"):
            base_columns.extend([
                {"label": _("Total Invoiced Amount"), "fieldname": "total_invoiced", "fieldtype": "Currency", "options": "currency", "width": 150},
                {"label": _("Total Ordered Amount"), "fieldname": "total_ordered", "fieldtype": "Currency", "options": "currency", "width": 150},
            ])
        
        base_columns.extend([
            {"label": _("Indent"), "fieldname": "indent", "fieldtype": "Int", "hidden": 1},
            {"label": _("Is Group"), "fieldname": "is_group", "fieldtype": "Int", "hidden": 1},
            {"label": _("Parent Customer"), "fieldname": "parent_customer", "fieldtype": "Data", "hidden": 1}
        ])
        
        self.columns = base_columns