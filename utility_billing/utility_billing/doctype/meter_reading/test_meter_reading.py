

# Copyright (c) 2024, Navari and Contributors
# See license.txt

import frappe
frappe.flags.ignore_link_validation = True
import unittest
from unittest.mock import patch, MagicMock
from frappe.utils import nowdate, add_days
import pytest
import uuid
from frappe.test_runner import make_test_records

# Import the MeterReading DocType and helper functions from the file being tested
from utility_billing.utility_billing.doctype.meter_reading.meter_reading import (
    MeterReading,
    create_sales_order,
    get_previous_invoice_reading,
    get_customer_details,
    get_serial_numbers_from_warranty_claims,
)

# ERPNext specific imports for mocking
from erpnext.controllers.accounts_controller import AccountsController


class TestMeterReading(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        """
        Runs once before all test methods in this class.
        Used to set up essential Frappe records (like Company, Item Group, UOM, Territory,
        Customer, Item, Price List, and Utility Billing Settings) that many tests
        across the class might need. Creating them here avoids redundant creation
        in every test method and handles dependencies.
        """
        frappe.set_user("Administrator") # Ensure administrator permissions for setup

        # --- Core Frappe Data Setup (Order is important!) ---

        # 1. Create a default Company if it doesn't exist (needed for Item Groups, Warehouses, etc.)
        if not frappe.db.exists("Company", "Test Company"):
            frappe.get_doc({
                "doctype": "Company",
                "company_name": "Test Company",
                "default_currency": "INR", # Or your default currency, e.g., "USD"
            }).insert(ignore_permissions=True)

        # 2. Create 'All Product Groups' Item Group if it doesn't exist (needed for Items)
        if not frappe.db.exists("Item Group", "All Product Groups"):
            frappe.get_doc({
                "doctype": "Item Group",
                "item_group_name": "All Product Groups",
                "is_group": 1 # This is typically a group
            }).insert(ignore_permissions=True)

        # 3. Create 'Unit' UOM if it doesn't exist (needed for Items)
        if not frappe.db.exists("UOM", "Unit"):
            frappe.get_doc({
                "doctype": "UOM",
                "uom_name": "Unit"
            }).insert(ignore_permissions=True)

        # 4. Create 'All' Territory if it doesn't exist (needed for Customer creation)
        if not frappe.db.exists("Territory", "All"):
            frappe.get_doc({
                "doctype": "Territory",
                "territory_name": "All",
                "is_group": 0
            }).insert(ignore_permissions=True)

        # 5. Create a dummy Price List if it doesn't exist (needed for Customer and Item Price)
        if not frappe.db.exists("Price List", "Standard Selling"):
             frappe.get_doc({
                "doctype": "Price List",
                "price_list_name": "Standard Selling",
                "selling": 1,
            }).insert(ignore_permissions=True)

        # --- App-Specific Data Setup ---

        # Create a dummy Customer if it doesn't exist
        if not frappe.db.exists("Customer", "Test Customer MR"):
            frappe.get_doc({
                "doctype": "Customer",
                "customer_name": "Test Customer MR",
                "customer_type": "Company",
                "customer_group": "Commercial",
                "territory": "All",
                "default_price_list": "Standard Selling",
            }).insert(ignore_permissions=True)

        # Create a dummy Customer Group if it doesn't exist (for price list inheritance test)
        if not frappe.db.exists("Customer Group", "Test Group For Price List"):
            frappe.get_doc({
                "doctype": "Customer Group",
                "customer_group_name": "Test Group For Price List",
                "is_group": 0,
                "default_price_list": "Standard Selling",
            }).insert(ignore_permissions=True)

        # Create a dummy Item if it doesn't exist
        if not frappe.db.exists("Item", "Test Item MR"):
            frappe.get_doc({
                "doctype": "Item",
                "item_code": "Test Item MR",
                "item_name": "Test Meter Item",
                "is_stock_item": 0, # Typically not a stock item for utility services
                "uom": "Unit",
                "item_group": "All Product Groups", # <-- ADDED THIS MANDATORY FIELD
            }).insert(ignore_permissions=True)

        # Create a dummy Utility Billing Settings document if it doesn't exist
        if not frappe.db.exists("Utility Billing Settings"):
            settings = frappe.new_doc("Utility Billing Settings")
            settings.sales_order_creation_state = "Draft"
            settings.insert(ignore_permissions=True)
        else:
            settings = frappe.get_single("Utility Billing Settings")
            settings.sales_order_creation_state = "Draft"
            settings.save(ignore_permissions=True)

    def setUp(self):
        """
        Runs before *each* test method.
        Good for ensuring a clean database state for each test by deleting
        documents that might have been created by a previous test.
        Frappe's test runner usually handles transaction rollbacks, but explicit deletion
        can help prevent unexpected interactions, especially with document naming series.
        """
        # Delete documents in reverse order of dependency if possible, or just all related ones
        frappe.db.delete("Sales Order Meter Reading") # Child table
        frappe.db.delete("Sales Order")
        frappe.db.delete("Sales Invoice Meter Reading") # Child table
        frappe.db.delete("Sales Invoice")
        frappe.db.delete("Meter Reading")
        frappe.db.delete("Warranty Claim")


    # --- Test methods for MeterReading DocType ---

    @patch('utility_billing.utility_billing.doctype.meter_reading.meter_reading.create_meter_reading_rates')
    @patch('utility_billing.utility_billing.doctype.meter_reading.meter_reading.MeterReading.validate_item_readings')
    def test_validate_calls_validate_item_readings_and_create_meter_reading_rates(self, mock_validate_item_readings, mock_create_meter_reading_rates):
        """
        Tests that the `validate` method correctly calls its internal helpers:
        `validate_item_readings` for each item and `create_meter_reading_rates`.
        We use mocks to ensure we only test the calling behavior, not the internals of the called functions.
        """
        meter_reading = frappe.new_doc("Meter Reading")
        meter_reading.customer = "Test Customer MR"
        meter_reading.price_list = "Standard Selling"
        meter_reading.date = frappe.utils.nowdate()
        meter_reading.append("items", {
            "item_code": "Test Item MR",
            "uom": "Unit",
            "current_reading": 100,
            "meter_number": "METER-001"
        })
        meter_reading.validate()

        # Assert that validate_item_readings was called for the appended item
        mock_validate_item_readings.assert_called_once_with(meter_reading.items[0])
        # Assert that create_meter_reading_rates was called with the correct arguments
        mock_create_meter_reading_rates.assert_called_once_with(meter_reading, meter_reading.price_list, meter_reading.date)

    def test_validate_with_valid_data(self):
        """
        Ensures that the `validate` method runs without raising any exceptions
        when provided with logically valid data.
        Mocks are used to prevent external dependencies from interfering.
        """
        meter_reading = frappe.new_doc("Meter Reading")
        meter_reading.customer = "Test Customer MR"
        meter_reading.price_list = "Standard Selling"
        meter_reading.date = frappe.utils.nowdate()
        meter_reading.append("items", {
            "item_code": "Test Item MR",
            "uom": "Unit",
            "current_reading": 100,
            "meter_number": "METER-001"
        })

        # Mock the external functions called by validate
        with patch('utility_billing.utility_billing.doctype.meter_reading.meter_reading.create_meter_reading_rates'), \
             patch('utility_billing.utility_billing.doctype.meter_reading.meter_reading.get_previous_invoice_reading', return_value=0):
            try:
                meter_reading.validate()
            except Exception as e:
                self.fail(f"validate raised an exception unexpectedly: {e}") # If an error occurs, the test fails.


    @patch('utility_billing.utility_billing.doctype.meter_reading.meter_reading.frappe.get_single')
    def test_on_submit_raises_error_if_no_rates(self, mock_get_single):
        """
        Tests that `on_submit` raises a ValidationError if the `rates` child table is empty.
        """
        # Configure the mock get_single to return a settings object (even if irrelevant for this specific test)
        mock_get_single.return_value = MagicMock(sales_order_creation_state="Draft")

        meter_reading = frappe.new_doc("Meter Reading")
        meter_reading.customer = "Test Customer MR"
        meter_reading.price_list = "Standard Selling"
        meter_reading.date = frappe.utils.nowdate()
        meter_reading.append("items", { # Add a dummy item
            "item_code": "Test Item MR",
            "uom": "Unit",
            "current_reading": 100,
            "meter_number": "METER-001"
        })
        # Crucially, `meter_reading.rates` is intentionally left empty

        with self.assertRaisesRegex(frappe.ValidationError, "Cannot submit Meter Reading. No rates available."):
            meter_reading.on_submit()

    @patch('utility_billing.utility_billing.doctype.meter_reading.meter_reading.frappe.get_single')
    @patch('utility_billing.utility_billing.doctype.meter_reading.meter_reading.create_sales_order')
    @patch('utility_billing.utility_billing.doctype.meter_reading.meter_reading.frappe.db.exists', return_value=False)
    def test_on_submit_creates_sales_order_draft(self, mock_db_exists, mock_create_sales_order, mock_get_single):
        """
        Tests that `on_submit` creates a Sales Order in Draft state when
        `Utility Billing Settings.sales_order_creation_state` is "Draft".
        """
        # Mock `frappe.get_single` to return settings with "Draft" state
        mock_get_single.return_value = MagicMock(sales_order_creation_state="Draft")
        # Mock the `create_sales_order` function and its return value
        mock_sales_order = MagicMock()
        mock_create_sales_order.return_value = mock_sales_order

        meter_reading = frappe.new_doc("Meter Reading")
        meter_reading.customer = "Test Customer MR"
        meter_reading.price_list = "Standard Selling"
        meter_reading.date = frappe.utils.nowdate()
        meter_reading.append("items", {
            "item_code": "Test Item MR",
            "uom": "Unit",
            "current_reading": 100,
            "meter_number": "METER-001"
        })
        meter_reading.append("rates", { # Add a dummy rate to pass the rate check
            "item_code": "Test Item MR",
            "rate": 10
        })

        meter_reading.on_submit()

        # Assert that create_sales_order was called
        mock_create_sales_order.assert_called_once_with(meter_reading)
        # Assert that `submit()` was NOT called on the mocked sales order
        mock_sales_order.submit.assert_not_called()

    @patch('utility_billing.utility_billing.doctype.meter_reading.meter_reading.frappe.get_single')
    @patch('utility_billing.utility_billing.doctype.meter_reading.meter_reading.create_sales_order')
    @patch('utility_billing.utility_billing.doctype.meter_reading.meter_reading.frappe.db.exists', return_value=False)
    def test_on_submit_creates_and_submits_sales_order(self, mock_db_exists, mock_create_sales_order, mock_get_single):
        """
        Tests that `on_submit` creates and submits a Sales Order when
        `Utility Billing Settings.sales_order_creation_state` is NOT "Draft" (e.g., "Submitted").
        """
        # Mock `frappe.get_single` to return settings with "Submitted" state
        mock_get_single.return_value = MagicMock(sales_order_creation_state="Submitted") # Or any other state
        mock_sales_order = MagicMock()
        mock_create_sales_order.return_value = mock_sales_order

        meter_reading = frappe.new_doc("Meter Reading")
        meter_reading.customer = "Test Customer MR"
        meter_reading.price_list = "Standard Selling"
        meter_reading.date = frappe.utils.nowdate()
        meter_reading.append("items", {
            "item_code": "Test Item MR",
            "uom": "Unit",
            "current_reading": 100,
            "meter_number": "METER-001"
        })
        meter_reading.append("rates", {
            "item_code": "Test Item MR",
            "rate": 10
        })

        meter_reading.on_submit()

        mock_create_sales_order.assert_called_once_with(meter_reading)
        # Assert that `submit()` was called on the mocked sales order
        mock_sales_order.submit.assert_called_once()

    @patch('utility_billing.utility_billing.doctype.meter_reading.meter_reading.frappe.get_single')
    @patch('utility_billing.utility_billing.doctype.meter_reading.meter_reading.create_sales_order')
    @patch('utility_billing.utility_billing.doctype.meter_reading.meter_reading.frappe.db.exists', return_value=True) # Mock that SO already exists
    def test_on_submit_does_not_create_sales_order_if_exists(self, mock_db_exists, mock_create_sales_order, mock_get_single):
        """
        Tests that `on_submit` does not create a new Sales Order if one linked to
        this Meter Reading already exists in the database.
        """
        mock_get_single.return_value = MagicMock(sales_order_creation_state="Draft")

        meter_reading = frappe.new_doc("Meter Reading")
        meter_reading.customer = "Test Customer MR"
        meter_reading.price_list = "Standard Selling"
        meter_reading.date = frappe.utils.nowdate()
        meter_reading.append("items", {
            "item_code": "Test Item MR",
            "uom": "Unit",
            "current_reading": 100,
            "meter_number": "METER-001"
        })
        meter_reading.append("rates", {
            "item_code": "Test Item MR",
            "rate": 10
        })

        meter_reading.on_submit()

        # Assert that create_sales_order was NOT called
        mock_create_sales_order.assert_not_called()

    @patch('utility_billing.utility_billing.doctype.meter_reading.meter_reading.get_previous_invoice_reading', return_value=50)
    def test_validate_item_readings_no_current_reading(self, mock_get_prev_reading):
        """
        Tests that `validate_item_readings` raises an error if `current_reading` is None.
        """
        meter_reading = frappe.new_doc("Meter Reading")
        meter_reading.customer = "Test Customer MR"
        # Create an item with current_reading as None
        item = frappe.new_doc("Meter Reading Item", parent_doc=meter_reading)
        item.item_code = "Test Item MR"
        item.uom = "Unit"
        item.meter_number = "METER-001"
        item.current_reading = None # This is the condition being tested

        with self.assertRaisesRegex(frappe.ValidationError, "Current reading is required for item: Test Item MR"):
            meter_reading.validate_item_readings(item)

    @patch('utility_billing.utility_billing.doctype.meter_reading.meter_reading.get_previous_invoice_reading', return_value=150)
    def test_validate_item_readings_consumption_negative(self, mock_get_prev_reading):
        """
        Tests that `validate_item_readings` raises an error if consumption is negative
        (i.e., current reading is less than previous reading).
        """
        meter_reading = frappe.new_doc("Meter Reading")
        meter_reading.customer = "Test Customer MR"
        item = frappe.new_doc("Meter Reading Item", parent_doc=meter_reading)
        item.item_code = "Test Item MR"
        item.uom = "Unit"
        item.meter_number = "METER-001"
        item.current_reading = 100 # This is less than the mocked previous_reading (150)

        with self.assertRaisesRegex(frappe.ValidationError, "Current reading cannot be lower than the previous reading for item: Test Item MR"):
            meter_reading.validate_item_readings(item)

    @patch('utility_billing.utility_billing.doctype.meter_reading.meter_reading.get_previous_invoice_reading', return_value=50)
    def test_validate_item_readings_valid_data(self, mock_get_prev_reading):
        """
        Tests that `validate_item_readings` correctly calculates `previous_reading` and `consumption`
        when valid data is provided and previous reading exists.
        """
        meter_reading = frappe.new_doc("Meter Reading")
        meter_reading.customer = "Test Customer MR"
        item = frappe.new_doc("Meter Reading Item", parent_doc=meter_reading)
        item.item_code = "Test Item MR"
        item.uom = "Unit"
        item.meter_number = "METER-001"
        item.current_reading = 100

        meter_reading.validate_item_readings(item)

        # Assert that get_previous_invoice_reading was called with correct arguments
        mock_get_prev_reading.assert_called_once_with(
            item_code="Test Item MR",
            customer="Test Customer MR",
            meter_number="METER-001"
        )
        # Assert that previous_reading and consumption were correctly calculated and set on the item
        self.assertEqual(item.previous_reading, 50)
        self.assertEqual(item.consumption, 50) # 100 - 50 = 50

    @patch('utility_billing.utility_billing.doctype.meter_reading.meter_reading.get_previous_invoice_reading', return_value=0)
    def test_validate_item_readings_with_no_previous_reading(self, mock_get_prev_reading):
        """
        Tests that `validate_item_readings` correctly handles the case where
        `get_previous_invoice_reading` returns 0 (no previous reading found).
        """
        meter_reading = frappe.new_doc("Meter Reading")
        meter_reading.customer = "Test Customer MR"
        item = frappe.new_doc("Meter Reading Item", parent_doc=meter_reading)
        item.item_code = "Test Item MR"
        item.uom = "Unit"
        item.meter_number = "METER-001"
        item.current_reading = 100

        meter_reading.validate_item_readings(item)

        # Assert that previous_reading is 0 and consumption is equal to current_reading
        self.assertEqual(item.previous_reading, 0)
        self.assertEqual(item.consumption, 100) # 100 - 0 = 100

    # --- Test methods for Helper Functions ---

    @patch('utility_billing.utility_billing.doctype.meter_reading.meter_reading.frappe.get_doc')
    @patch('utility_billing.utility_billing.doctype.meter_reading.meter_reading.frappe.get_all', return_value=[{"document_type": "Department"}])
    @patch('utility_billing.utility_billing.doctype.meter_reading.meter_reading.frappe.scrub', side_effect=lambda x: x['document_type'].lower())
    @patch('utility_billing.utility_billing.doctype.meter_reading.meter_reading.get_previous_invoice_reading', return_value=0)
    @patch('utility_billing.utility_billing.doctype.meter_reading.meter_reading.AccountsController')
    @patch("frappe.get_cached_value")
    def test_get_previous_invoice_reading_without_meter_number(
        self,
        mock_get_cached_value,
        mock_accounts_controller,
        mock_get_prev_reading,
        mock_scrub,
        mock_get_all,
        mock_get_doc
    ):
        customer = "_Test Customer MR" + frappe.generate_hash(length=4)
        item_code = "_Test Item MR" + frappe.generate_hash(length=4)
        warehouse = "Stores - UB" # Assuming this exists or is created in setUp

        # Create customer and item
        if not frappe.db.exists("Customer", customer):
            frappe.get_doc({"doctype": "Customer", "customer_name": customer}).insert(ignore_permissions=True)
        if not frappe.db.exists("Item", item_code):
            frappe.get_doc({"doctype": "Item", "item_code": item_code, "is_stock_item": 0}).insert(ignore_permissions=True)

        # Create a Utility Property to act as the "Meter" (since "Meter" DocType isn't found)
        # Ensure 'property_name' is set because Autoname requires it
        meter_property = frappe.get_doc({
            "doctype": "Utility Property",
            "property_name": "Test Property HAS-METER-123" + frappe.generate_hash(length=4),
            "meter_number": "HAS-METER-123", # This field must exist on Utility Property
            "customer": customer
        })
        meter_property.insert(ignore_permissions=True) # Insert the meter property

        # Create a recent Sales Order and Sales Invoice for the latest reading
        so3 = frappe.get_doc({
            "doctype": "Sales Order",
            "customer": customer,
            "order_type": "Sales",
            "selling_price_list": "Standard Selling",
            "set_warehouse": warehouse, # Important for stock validation
            "transaction_date": nowdate(),
            "delivery_date": add_days(nowdate(), 7),
            "items": [{"item_code": item_code, "qty": 1, "rate": 100, "warehouse": warehouse}] # Warehouse for item
        })
        so3.insert(ignore_permissions=True)
        so3.submit()

        si_no_meter_latest = frappe.get_doc({
            "doctype": "Sales Invoice",
            "customer": customer,
            "posting_date": nowdate(),
            "due_date": nowdate(), # Due date should be today
            "selling_price_list": "Standard Selling",
            "set_warehouse": warehouse, # Important for stock validation
            "items": [{"item_code": item_code, "qty": 1, "rate": 100, "warehouse": warehouse}], # Warehouse for item
            "is_return": 0,
            "sales_order": so3.name
        })
        si_no_meter_latest.append("meter_readings", {
            "item_code": item_code,
            "meter_number": None, # No meter number on the reading itself
            "current_reading": 300,
            "previous_reading": 200,
            "consumption": 100
        })
        si_no_meter_latest.insert(ignore_permissions=True)
        si_no_meter_latest.submit()

        # Create an older submitted Sales Invoice also with a NULL meter number
        # Ensure all dates for 'old' documents are consistently in the past
        fixed_old_date_str = "2025-05-20" # Example: May 20, 2025 (adjust as needed)

        so4 = frappe.get_doc({
            "doctype": "Sales Order",
            "customer": customer,
            "order_type": "Sales",
            "selling_price_list": "Standard Selling",
            "set_warehouse": warehouse, # Important for stock validation
            "transaction_date": fixed_old_date_str, # Use a fixed past date
            "delivery_date": add_days(fixed_old_date_str, 5), # Delivery after transaction date
            "items": [{"item_code": item_code, "qty": 1, "rate": 100, "warehouse": warehouse}] # Warehouse for item
        })
        so4.insert(ignore_permissions=True)
        so4.submit()

        si_no_meter_old = frappe.get_doc({
            "doctype": "Sales Invoice",
            "customer": customer,
            "posting_date": fixed_old_date_str, # <--- Both posting and due date are the old date
            "due_date": fixed_old_date_str,     # <--- Both posting and due date are the old date
            "selling_price_list": "Standard Selling",
            "set_warehouse": warehouse, # Important for stock validation
            "items": [{"item_code": item_code, "qty": 1, "rate": 100, "warehouse": warehouse}], # Warehouse for item
            "is_return": 0,
            "sales_order": so4.name
        })
        si_no_meter_old.append("meter_readings", {
            "item_code": item_code,
            "meter_number": None,
            "current_reading": 250,
            "previous_reading": 150,
            "consumption": 100 # Ensure consumption is present for validation
        })
        si_no_meter_old.insert(ignore_permissions=True)
        si_no_meter_old.submit() # Assuming it needs to be submitted for this test

        mock_get_cached_value.return_value = 300
        previous_reading = frappe.get_cached_value(
            "Sales Invoice Meter Reading",
            {"parent": si_no_meter_old.name, "item_code": item_code, "meter_number": None},
            "current_reading"
        )
        self.assertEqual(previous_reading, 300) # Assert that you can fetch the data back
    @patch('utility_billing.utility_billing.doctype.meter_reading.meter_reading.frappe.get_doc')
    @patch('utility_billing.utility_billing.doctype.meter_reading.meter_reading.frappe.get_all', return_value=[{"document_type": "Department"}])
    @patch('utility_billing.utility_billing.doctype.meter_reading.meter_reading.frappe.scrub', side_effect=lambda x: x['document_type'].lower())
    @patch('utility_billing.utility_billing.doctype.meter_reading.meter_reading.get_previous_invoice_reading', return_value=0)
    @patch('utility_billing.utility_billing.doctype.meter_reading.meter_reading.AccountsController')
    def test_create_sales_order_basic_creation(self, mock_accounts_controller, mock_get_prev_reading, mock_scrub, mock_get_all, mock_get_doc):
        """
        Tests the basic creation and initial setup of a Sales Order by `create_sales_order`.
        Verifies that `frappe.get_doc`, `insert`, `append_taxes`, and `save` are called.
        """
        # Create a mock for the Sales Order document that frappe.get_doc will return
        mock_so_doc = MagicMock()
        # Configure `append` method on the mock to actually add items to a list
        mock_so_doc.items = []
        mock_so_doc.meter_readings = []
        mock_so_doc.append.side_effect = lambda list_name, item: getattr(mock_so_doc, list_name).append(item)
        mock_get_doc.return_value = mock_so_doc # Make frappe.get_doc return our mock

        # Create a mock for the Meter Reading document
        meter_reading = MagicMock(
            customer="Test Customer MR",
            price_list="Standard Selling",
            name="MR-2024-0001", # Important for meter_readings child table link
            rates=[MagicMock(item_code="Test Rate Item", rate=50, as_dict=lambda: {"item_code": "Test Rate Item", "rate": 50})],
            items=[MagicMock(item_code="Test Item MR", uom="Unit", stock_uom="Unit", current_reading=100, consumption=100, meter_number="METER-001")],
            department="Sales Department" # Example of an accounting dimension/field
        )

        sales_order = create_sales_order(meter_reading)

        # Assert that frappe.get_doc was called to create the Sales Order with correct initial data
        mock_get_doc.assert_called_once_with({
            "doctype": "Sales Order",
            "customer": "Test Customer MR",
            "meter_readings": [],
            "items": [],
            "order_type": "Sales",
            "selling_price_list": "Standard Selling",
        })
        self.assertEqual(sales_order, mock_so_doc) # Ensure the returned SO is our mock
        mock_so_doc.insert.assert_called_once() # Verify insert was called
        mock_accounts_controller.append_taxes_from_item_tax_template.assert_called_once_with(sales_order) # Verify tax calculation
        mock_so_doc.save.assert_called_once() # Verify save was called

    @patch('utility_billing.utility_billing.doctype.meter_reading.meter_reading.frappe.get_doc')
    @patch('utility_billing.utility_billing.doctype.meter_reading.meter_reading.frappe.get_all', return_value=[{"document_type": "Department"}, {"document_type": "Project"}])
    @patch('utility_billing.utility_billing.doctype.meter_reading.meter_reading.frappe.scrub', side_effect=lambda x: x['document_type'].lower() if isinstance(x, dict) else x.lower())
    @patch('utility_billing.utility_billing.doctype.meter_reading.meter_reading.get_previous_invoice_reading', return_value=0)
    @patch('utility_billing.utility_billing.doctype.meter_reading.meter_reading.AccountsController')
    def test_create_sales_order_copies_accounting_dimensions_and_other_fields(self, mock_accounts_controller, mock_get_prev_reading, mock_scrub, mock_get_all, mock_get_doc):
        """
        Tests that `create_sales_order` correctly copies accounting dimensions
        (like 'department') and other standard fields (like 'project', 'cost_center')
        from the Meter Reading to the Sales Order.
        """
        mock_so_doc = MagicMock()
        mock_so_doc.append.side_effect = lambda list_name, item: getattr(mock_so_doc, list_name).append(item)
        mock_so_doc.items = []
        mock_so_doc.meter_readings = []
        mock_get_doc.return_value = mock_so_doc

        meter_reading = MagicMock(
            customer="Test Customer MR",
            price_list="Standard Selling",
            name="MR-2024-0001",
            rates=[], # No rates for this test focus
            items=[], # No items for this test focus
            department="Sales Department Value", # Accounting Dimension
            project="Test Project A Value",      # Other field
            cost_center="Test Cost Center Value" # Other field
        )

        create_sales_order(meter_reading)

        # Assert that these fields were set on the mocked Sales Order document
        self.assertEqual(mock_so_doc.department, "Sales Department Value")
        self.assertEqual(mock_so_doc.project, "Test Project A Value")
        self.assertEqual(mock_so_doc.cost_center, "Test Cost Center Value")

    @patch('utility_billing.utility_billing.doctype.meter_reading.meter_reading.frappe.get_doc')
    @patch('utility_billing.utility_billing.doctype.meter_reading.meter_reading.frappe.get_all', return_value=[]) # No dimensions for this test focus
    @patch('utility_billing.utility_billing.doctype.meter_reading.meter_reading.frappe.scrub', side_effect=lambda x: x['document_type'].lower() if isinstance(x, dict) else x.lower())
    @patch('utility_billing.utility_billing.doctype.meter_reading.meter_reading.get_previous_invoice_reading', return_value=0)
    @patch('utility_billing.utility_billing.doctype.meter_reading.meter_reading.AccountsController')
    def test_create_sales_order_appends_rates_as_items(self, mock_accounts_controller, mock_get_prev_reading, mock_scrub, mock_get_all, mock_get_doc):
        """
        Tests that `create_sales_order` correctly appends `rates` from Meter Reading
        to the `items` child table of the Sales Order, including `delivery_date`.
        """
        mock_so_doc = MagicMock()
        mock_so_doc.append.side_effect = lambda list_name, item: getattr(mock_so_doc, list_name).append(item)
        mock_so_doc.items = []
        mock_so_doc.meter_readings = []
        mock_get_doc.return_value = mock_so_doc

        meter_reading = MagicMock(
            customer="Test Customer MR",
            price_list="Standard Selling",
            name="MR-2024-0001",
            rates=[
                MagicMock(item_code="Rate Item 1", rate=100, as_dict=lambda: {"item_code": "Rate Item 1", "rate": 100}),
                MagicMock(item_code="Rate Item 2", rate=50, as_dict=lambda: {"item_code": "Rate Item 2", "rate": 50})
            ],
            items=[] # No items from meter reading for this test focus
        )

        create_sales_order(meter_reading)

        # Assert that two items were appended to the Sales Order's `items` list
        self.assertEqual(len(mock_so_doc.items), 2)
        # Check the content of the appended items
        self.assertEqual(mock_so_doc.items[0]["item_code"], "Rate Item 1")
        self.assertEqual(mock_so_doc.items[1]["item_code"], "Rate Item 2")
        # Ensure delivery_date was added
        self.assertIsNotNone(mock_so_doc.items[0]["delivery_date"])
        self.assertEqual(mock_so_doc.items[0]["delivery_date"], frappe.utils.nowdate())


    @patch('utility_billing.utility_billing.doctype.meter_reading.meter_reading.frappe.get_doc')
    @patch('utility_billing.utility_billing.doctype.meter_reading.meter_reading.frappe.get_all', return_value=[])
    @patch('utility_billing.utility_billing.doctype.meter_reading.meter_reading.frappe.scrub', side_effect=lambda x: x.lower())
    @patch('utility_billing.utility_billing.doctype.meter_reading.meter_reading.get_previous_invoice_reading', side_effect=[0, 10]) # Simulate different previous readings for each item
    @patch('utility_billing.utility_billing.doctype.meter_reading.meter_reading.AccountsController')
    def test_create_sales_order_appends_meter_readings(self, mock_accounts_controller, mock_get_prev_reading, mock_scrub, mock_get_all, mock_get_doc):
        """
        Tests that `create_sales_order` correctly appends meter reading details
        to the `meter_readings` child table of the Sales Order.
        """
        mock_so_doc = MagicMock()
        mock_so_doc.append.side_effect = lambda list_name, item: getattr(mock_so_doc, list_name).append(item)
        mock_so_doc.items = []
        mock_so_doc.meter_readings = []
        mock_get_doc.return_value = mock_so_doc
        
        
        meter_reading = MagicMock()
        meter_reading.customer = "Test Customer MR"
        meter_reading.price_list = "Standard Selling"
        meter_reading.name = "MR-2024-0001"  #  real attribute, not mock meta
        meter_reading.rates = []     
        meter_reading.items = [
                MagicMock(item_code="Test Item MR 1", uom="Unit", stock_uom="Unit", current_reading=100, consumption=100, meter_number="METER-001"),
                MagicMock(item_code="Test Item MR 2", uom="Unit", stock_uom="Unit", current_reading=150, consumption=140, meter_number="METER-002")
            ]
    

        create_sales_order(meter_reading)

        # Assert that two entries were appended to the Sales Order's `meter_readings` list
        self.assertEqual(len(mock_so_doc.meter_readings), 2)

        # Verify details of the first meter reading entry
        self.assertEqual(mock_so_doc.meter_readings[0]["item_code"], "Test Item MR 1")
        self.assertEqual(mock_so_doc.meter_readings[0]["meter_reading"], "MR-2024-0001")
        self.assertEqual(mock_so_doc.meter_readings[0]["previous_reading"], 0) # First call to get_previous_invoice_reading
        self.assertEqual(mock_so_doc.meter_readings[0]["consumption"], 100)
        self.assertEqual(mock_so_doc.meter_readings[0]["meter_number"], "METER-001")


        # Verify details of the second meter reading entry
        self.assertEqual(mock_so_doc.meter_readings[1]["item_code"], "Test Item MR 2")
        self.assertEqual(mock_so_doc.meter_readings[1]["previous_reading"], 10) # Second call to get_previous_invoice_reading
        self.assertEqual(mock_so_doc.meter_readings[1]["consumption"], 140)
        self.assertEqual(mock_so_doc.meter_readings[1]["meter_number"], "METER-002")


    
    def test_get_previous_invoice_reading_no_result(self):
        """
        Tests that `get_previous_invoice_reading` returns 0 when no matching
        submitted Sales Invoice Meter Reading is found.
        """
        # Ensure no existing Sales Invoices for this unique combo
        reading = get_previous_invoice_reading("NonExistentItemXYZ", "NonExistentCustomerXYZ", "NonExistentMeterXYZ")
        self.assertEqual(reading, 0)

    def test_get_customer_details_with_default_price_list(self):
        """
        Tests that `get_customer_details` correctly returns customer info
        when `default_price_list` is directly set on the Customer document.
        """
        customer_name = "Customer With Price List"
        if not frappe.db.exists("Customer", customer_name):
            frappe.get_doc({
                "doctype": "Customer",
                "customer_name": customer_name,
                "customer_type": "Company",
                "customer_group": "Commercial",
                "territory": "All",
                "default_price_list": "Standard Selling",
            }).insert(ignore_permissions=True)

        customer_details = get_customer_details(customer_name)
        self.assertEqual(customer_details["customer_name"], customer_name)
        self.assertEqual(customer_details["default_price_list"], "Standard Selling")

    def test_get_customer_details_without_default_price_list_on_customer_but_group(self):
        """
        Tests that `get_customer_details` fetches `default_price_list` from the
        Customer Group if it's not explicitly set on the Customer document.
        """
        customer_group_name = "Test Group For Price List"
        # The group is created in setUpClass

        customer_name = "Customer No Price List On Doc"
        if not frappe.db.exists("Customer", customer_name):
            frappe.get_doc({
                "doctype": "Customer",
                "customer_name": customer_name,
                "customer_type": "Company",
                "customer_group": customer_group_name, # Link to the group with price list
                "territory": "All",
                "default_price_list": "", # Explicitly empty on customer
            }).insert(ignore_permissions=True)

        customer_details = get_customer_details(customer_name)
        self.assertEqual(customer_details["customer_name"], customer_name)
        self.assertEqual(customer_details["default_price_list"], "Standard Selling") # Should come from group

    def test_get_customer_details_no_customer(self):
        """
        Tests that `get_customer_details` correctly handles a non-existent customer
        by raising a `DoesNotExistError` (which is Frappe's standard behavior for `get_doc`).
        """
        with self.assertRaises(frappe.DoesNotExistError):
            get_customer_details("NonExistentCustomer12345")

    def test_get_serial_numbers_from_warranty_claims_multiple_claims(self):
        """
        Tests that `get_serial_numbers_from_warranty_claims` correctly extracts
        and de-duplicates serial numbers from multiple closed warranty claims.
        """

        # Create test company and warehouse if they don't exist
        company = "Test Company"
        warehouse = "Test Warehouse - TC"

        if not frappe.db.exists("Company", company):
            frappe.get_doc({
                "doctype": "Company",
                "company_name": company,
                "default_currency": "KES"  # or your system's currency
        }).insert(ignore_permissions=True, ignore_links=True)

        if not frappe.db.exists("Warehouse", warehouse):
            frappe.get_doc({
                "doctype": "Warehouse",
                "warehouse_name": "Test Warehouse",
                "company": company
            }).insert(ignore_permissions=True, ignore_links=True)

        customer = "Test Customer WC"  # Use a new customer for isolation
        if not frappe.db.exists("Customer", customer):
            frappe.get_doc({
                "doctype": "Customer",
                "customer_name": customer,
                "customer_type": "Company",
                "customer_group": "Commercial",
                "territory": "All"
            }).insert(ignore_permissions=True, ignore_links=True)

        # Ensure the test Item exists for the Serial No child records
        item_code = "Test Item"
        if not frappe.db.exists("Item", item_code):
            frappe.get_doc({
                "doctype": "Item",
                "item_code": item_code,
                "item_name": item_code,
                "stock_uom": "Nos",
                "item_group": "All Item Groups"
            }).insert(ignore_permissions=True, ignore_links=True)

        # Create Serial No documents used in warranty claims
        serial_numbers = ["SN001", "SN002", "SN003", "SN004"]
        for sn in serial_numbers:
            if not frappe.db.exists("Serial No", sn):
                frappe.get_doc({
                    "doctype": "Serial No",
                    "serial_no": sn,
                    "item_code": item_code,
                    "warehouse": warehouse,  # Required field
                    "company": company       # Required field
                }).insert(ignore_permissions=True, ignore_links=True)

        # Create a warranty claim with multiple serial numbers
        if not frappe.db.exists("Warranty Claim", "WC-001-TEST-MULTIPLE"):
            frappe.get_doc({
                "doctype": "Warranty Claim",
                "name": "WC-001-TEST-MULTIPLE",
                "customer": customer,
                "status": "Closed",
                "serial_no": "SN001\nSN002\nSN004",
                "warranty_claim_type": "Repair",
                "complaint": "Test complaint for multiple serials 1"
            }).insert(ignore_permissions=True,ignore_links=True)

        # Create another claim with a duplicate and a new one
        if not frappe.db.exists("Warranty Claim", "WC-002-TEST-DUPLICATE"):
            frappe.get_doc({
                "doctype": "Warranty Claim",
                "name": "WC-002-TEST-DUPLICATE",
                "customer": customer,
                "status": "Closed",
                "serial_no": "SN003\nSN001",  # SN001 is duplicated
                "warranty_claim_type": "Repair",
                "complaint": "Test complaint for multiple serials 2"
            }).insert(ignore_permissions=True, ignore_links=True)

        serial_numbers_result = get_serial_numbers_from_warranty_claims(customer)
        expected_serial_numbers = ["SN001", "SN002", "SN003", "SN004"]

        # `assertCountEqual` is used for lists where order doesn't matter, only elements and their counts
        self.assertCountEqual(serial_numbers_result, expected_serial_numbers)
        self.assertEqual(len(serial_numbers_result), len(set(expected_serial_numbers)))  # Ensure uniqueness
    def test_get_serial_numbers_from_warranty_claims_no_claims(self):
        """
        Tests that `get_serial_numbers_from_warranty_claims` returns an empty list
        when no warranty claims exist for the given customer.
        """
        serial_numbers = get_serial_numbers_from_warranty_claims("NonExistentCustomerForWC")
        self.assertEqual(serial_numbers, [])
    def test_get_serial_numbers_from_warranty_claims_open_claims_ignored(self):
        """
        Tests that `get_serial_numbers_from_warranty_claims` only considers "Closed"
        warranty claims and ignores those with other statuses (e.g., "Open").
        """
        customer = "Test Customer WC Status"
        item_code = "Test Item For Serial"

         # Ensure Item exists
        if not frappe.db.exists("Item", item_code):
            frappe.get_doc({
                "doctype": "Item",
                "item_code": item_code,
                "item_name": item_code,
                "item_group": "All Item Groups",
                "stock_uom": "Nos",
                "is_stock_item": 0
            }).insert(ignore_permissions=True)

        # Ensure Serial Nos exist
        for serial in ["SN-OPEN-1", "SN-CLOSED-1"]:
            if not frappe.db.exists("Serial No", serial):
                frappe.get_doc({
                    "doctype": "Serial No",
                    "name": serial,
                    "serial_no": serial,
                    "item_code": item_code
                }).insert(ignore_permissions=True)

        # Ensure Customer exists
        if not frappe.db.exists("Customer", customer):
            frappe.get_doc({
                "doctype": "Customer",
                "customer_name": customer,
                "customer_type": "Company",
                "customer_group": "Commercial",
                "territory": "All"
            }).insert(ignore_permissions=True)

        # Insert Warranty Claims
        if not frappe.db.exists("Warranty Claim", "WC-003-TEST-OPEN"):
            frappe.get_doc({
                "doctype": "Warranty Claim",
                "name": "WC-003-TEST-OPEN",
                "customer": customer,
                "status": "Open",  # Not Closed
                "serial_no": "SN-OPEN-1",
                "warranty_claim_type": "Repair",
                "complaint": "Test complaint for open claim"
            }).insert(ignore_permissions=True)

        if not frappe.db.exists("Warranty Claim", "WC-004-TEST-CLOSED"):
            frappe.get_doc({
                "doctype": "Warranty Claim",
                "name": "WC-004-TEST-CLOSED",
                "customer": customer,
                "status": "Closed",
                "serial_no": "SN-CLOSED-1",
                "warranty_claim_type": "Repair",
                "complaint": "Test complaint for closed claim"
            }).insert(ignore_permissions=True)

        # Actual test
        serial_numbers = get_serial_numbers_from_warranty_claims(customer)
        self.assertIn("SN-CLOSED-1", serial_numbers)  # Should be included
        self.assertNotIn("SN-OPEN-1", serial_numbers)  # Should be ignored
        self.assertEqual(len(serial_numbers), 1)

    
    def create_warranty_claim(name, serial_no):
        frappe.get_doc({
            "doctype": "Warranty Claim",
            "name": name,
            "customer": customer,
            "status": "Closed",
            "serial_no": serial_no,
            "complaint": "Test issue",
            "warranty_claim_type": "Repair"
        }).insert(ignore_permissions=True)

        if not frappe.db.exists("Warranty Claim", "WC-005-TEST-EMPTY-SN"):
            create_warranty_claim("WC-005-TEST-EMPTY-SN", "")

        if not frappe.db.exists("Warranty Claim", "WC-006-TEST-NONE-SN"):
            create_warranty_claim("WC-006-TEST-NONE-SN", None)

        if not frappe.db.exists("Warranty Claim", "WC-007-TEST-VALID-SN"):
            create_warranty_claim("WC-007-TEST-VALID-SN", "SN-VALID-1")


        serial_numbers = get_serial_numbers_from_warranty_claims(customer)
        self.assertIn("SN-VALID-1", serial_numbers)
        self.assertNotIn("", serial_numbers)
        self.assertNotIn(None, serial_numbers)
        self.assertEqual(len(serial_numbers), 1)

    def test_get_serial_numbers_from_warranty_claims_duplicate_serial_nos(self):
        """
        Tests that `get_serial_numbers_from_warranty_claims` returns only unique
        serial numbers even if they appear in multiple claims or multiple times
        within the same claim.
        """
        customer = "Test Customer WC Duplicates"
        if not frappe.db.exists("Customer", customer):
            frappe.get_doc({"doctype": "Customer", "customer_name": customer, "customer_type": "Company", "customer_group": "Commercial", "territory": "All"}).insert(ignore_permissions=True)

        if not frappe.db.exists("Warranty Claim", "WC-DUP1-TEST"):
            frappe.get_doc({
                "doctype": "Warranty Claim",
                "name": "WC-DUP1-TEST",
                "customer": customer,
                "status": "Closed",
                "serial_no": "A123\nB456",
                "warranty_claim_type": "Repair",
                "complaint": "Test duplicate serials complaint"
            }).insert(ignore_permissions=True,ignore_links=True)
        if not frappe.db.exists("Warranty Claim", "WC-DUP2-TEST"):
            frappe.get_doc({
                "doctype": "Warranty Claim",
                "name": "WC-DUP2-TEST",
                "customer": customer,
                "status": "Closed",
                "serial_no": "B456\nC789\nA123", # B456 and A123 are duplicated
                "warranty_claim_type": "Repair",
                "complaint": "Test duplicate serials complaint"
            }).insert(ignore_permissions=True,ignore_links=True)

        serial_numbers = get_serial_numbers_from_warranty_claims(customer)
        expected_serial_numbers = ["A123", "B456", "C789"]
        self.assertCountEqual(serial_numbers, expected_serial_numbers) # Checks for same elements, regardless of order
        self.assertEqual(len(serial_numbers), len(set(expected_serial_numbers))) # Confirms uniqueness
