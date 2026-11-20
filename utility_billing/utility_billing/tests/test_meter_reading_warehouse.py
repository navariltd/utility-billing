"""Tests for the warehouse of Meter Reading rows.

As on Stock Entry, a row without a warehouse takes the header Warehouse on
save, so imports and API saves behave as the form does. A row's own warehouse
is kept, and a reading without a header Warehouse behaves as before.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import today

from utility_billing.utility_billing.doctype.meter_reading.meter_reading import set_row_warehouses

ITEM = "_Test Reading Warehouse Item"
PRICE_LIST = "_Test Reading Warehouse List"


class TestSetRowWarehouses(FrappeTestCase):
    def reading(self, header, *rows):
        doc = frappe.new_doc("Meter Reading")
        doc.warehouse = header
        for warehouse in rows:
            doc.append("items", {"warehouse": warehouse})
        set_row_warehouses(doc)
        return [row.warehouse for row in doc.items]

    def test_rows_without_a_warehouse_take_the_header(self):
        self.assertEqual(self.reading("Header", None, None), ["Header", "Header"])

    def test_a_row_keeps_its_own_warehouse(self):
        self.assertEqual(self.reading("Header", "Own", None), ["Own", "Header"])

    def test_without_a_header_nothing_changes(self):
        self.assertEqual(self.reading(None, None, "Own"), [None, "Own"])


class TestSavedReading(FrappeTestCase):
    def setUp(self):
        self.company = frappe.db.get_value("Company", {}, "name")
        self.currency = frappe.get_cached_value("Company", self.company, "default_currency")
        self.warehouses = frappe.get_all("Warehouse", filters={"company": self.company, "is_group": 0}, pluck="name", limit=2)
        self.customer = frappe.get_doc(
            {"doctype": "Customer", "customer_name": "_Test Reading Warehouse", "customer_type": "Individual"}
        ).insert(ignore_permissions=True).name
        if not frappe.db.exists("Price List", PRICE_LIST):
            frappe.get_doc(
                {"doctype": "Price List", "price_list_name": PRICE_LIST, "selling": 1, "currency": self.currency}
            ).insert(ignore_permissions=True)
        if not frappe.db.exists("Item", ITEM):
            frappe.get_doc(
                {
                    "doctype": "Item",
                    "item_code": ITEM,
                    "item_group": frappe.db.get_value("Item Group", {"is_group": 0}, "name"),
                    "stock_uom": "Nos",
                    "is_stock_item": 0,
                    "is_sales_item": 1,
                    "is_utility_item": 1,
                }
            ).insert(ignore_permissions=True)
        frappe.get_doc(
            {"doctype": "Item Price", "item_code": ITEM, "price_list": PRICE_LIST, "price_list_rate": 5, "valid_from": "2000-01-01"}
        ).insert(ignore_permissions=True)

    def tearDown(self):
        frappe.db.rollback()

    def save(self, header, row):
        return frappe.get_doc(
            {
                "doctype": "Meter Reading",
                "customer": self.customer,
                "company": self.company,
                "currency": self.currency,
                "date": today(),
                "price_list": PRICE_LIST,
                "warehouse": header,
                "items": [{"item_code": ITEM, "current_reading": 10, "warehouse": row, "uom": "Nos", "stock_uom": "Nos"}],
            }
        ).insert(ignore_permissions=True)

    def test_a_row_without_a_warehouse_takes_the_header_on_save(self):
        reading = self.save(self.warehouses[0], None)

        self.assertEqual(reading.items[0].warehouse, self.warehouses[0])
        self.assertEqual({rate.warehouse for rate in reading.rates}, {self.warehouses[0]})

    def test_a_row_set_by_hand_keeps_its_warehouse(self):
        if len(self.warehouses) < 2:
            self.skipTest("needs two warehouses")

        self.assertEqual(self.save(self.warehouses[0], self.warehouses[1]).items[0].warehouse, self.warehouses[1])

    def test_without_a_header_a_row_still_needs_its_warehouse(self):
        with self.assertRaises(frappe.MandatoryError):
            self.save(None, None)
