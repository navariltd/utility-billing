import frappe
import json
from frappe.tests.utils import FrappeTestCase
from frappe.utils import nowdate, add_months
from utility_billing.utility_billing.doctype.utility_service_request.utility_service_request import (
    create_contract,
    make_customer,
    create_site_survey,
    create_stock_entry_for_meter_issue,
    create_sales_order_doc,
    create_sales_invoice_doc,
    get_utility_bill_structure_details,
)


class TestUtilityServiceRequest(FrappeTestCase):
    

    def setUp(self):
        """Initialize test customer, item, and utility bill structure"""
        self.created_docs = []

        self.customer = frappe.get_doc({
            "doctype": "Customer",
            "customer_name": "Test Customer",
            "customer_type": "Individual"
        }).insert()
        self.created_docs.append(("Customer", self.customer.name))

        self.item = frappe.get_doc({
            "doctype": "Item",
            "item_code": "TEST-ITEM",
            "item_name": "Test Item",
            "stock_uom": "Nos",
            "item_group": "Products",
            "is_stock_item": 0,
            "standard_rate": 100
        }).insert()
        self.created_docs.append(("Item", self.item.name))

        self.bill_structure = frappe.get_doc({
            "doctype": "Utility Bill Structure",
            "utility_bill_structure_name": "Test Structure",
            "cost_center": "Main - TC",
            "items": [{"item": self.item.name, "amount": 100}]
        }).insert()
        self.created_docs.append(("Utility Bill Structure", self.bill_structure.name))

    def tearDown(self):
        """Deletes all created test documents"""
        for doctype, name in reversed(self.created_docs):
            frappe.delete_doc(doctype, name, force=True)
        frappe.db.rollback()

    def create_utility_service_request(self, overrides=None):
        """Helper to create and insert a Utility Service Request"""
        doc = frappe.get_doc({
            "doctype": "Utility Service Request",
            "service_request_from": "Customer",
            "party_name": self.customer.name,
            "utility_bill_structure": self.bill_structure.name,
            "start_date": nowdate(),
            "contract_length_months": 3,
            **(overrides or {})
        })
        doc.insert()
        self.created_docs.append(("Utility Service Request", doc.name))
        return doc


    def test_validate_contract_dates_auto_sets_end_date(self):
        """Test that end_date is auto-calculated from start_date and duration"""
        usr = self.create_utility_service_request()
        usr.validate_contract_dates()
        expected_end = add_months(usr.start_date, usr.contract_length_months)
        self.assertEqual(str(usr.end_date), str(expected_end))

    def test_on_submit_creates_customer_when_enabled(self):
        """Test that customer is created on submit when enabled in settings"""
        settings = frappe.get_doc("Utility Billing Settings", "Utility Billing Settings")
        settings.create_customer_from_utility_service_request_on_submit = 1
        settings.save()

        usr = self.create_utility_service_request()
        usr.submit()
        self.assertTrue(usr.customer)


    def test_create_contract_success(self):
        """Test successful contract creation from service request"""
        usr = self.create_utility_service_request()
        contract_name = create_contract(usr.name)
        self.created_docs.append(("Contract", contract_name))
        self.assertEqual(frappe.get_doc("Contract", contract_name).utility_service_request, usr.name)


    def test_get_utility_bill_structure_details_returns_items(self):
        """Test that bill structure fetch returns valid item details"""
        result = get_utility_bill_structure_details(self.bill_structure.name)
        self.assertTrue(result.get("items"))
        self.assertEqual(result["items"][0]["item_code"], self.item.item_code)

    def test_create_sales_order_doc_creates_order_successfully(self):
        """Test creating a Sales Order from a service request"""
        usr = self.create_utility_service_request()
        items = self.get_items_list()
        so_name = create_sales_order_doc(
            docname=usr.name,
            items=json.dumps(items),
            customer=self.customer.name,
            transaction_date=nowdate(),
            company="Test Company"
        )
        self.created_docs.append(("Sales Order", so_name))
        self.assertTrue(so_name)
        self.assertEqual(frappe.get_doc("Sales Order", so_name).customer, self.customer.name)

    def test_create_sales_invoice_doc_creates_invoice_successfully(self):
        """Test creating a Sales Invoice from a service request"""
        usr = self.create_utility_service_request()
        items = self.get_items_list()
        si_name = create_sales_invoice_doc(
            docname=usr.name,
            items=json.dumps(items),
            customer=self.customer.name,
            posting_date=nowdate(),
            company="Test Company"
        )
        self.created_docs.append(("Sales Invoice", si_name))
        self.assertTrue(si_name)
        self.assertEqual(frappe.get_doc("Sales Invoice", si_name).customer, self.customer.name)
