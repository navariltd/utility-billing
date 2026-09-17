"""Shared record factories for the Item Price schedule tests.

The scheduled-billing tests all need the same handful of records: a sales item,
a selling price list, a utility property owning a rent service item, and a
customer. Centralising them keeps each test file focused on the behaviour it
verifies instead of repeating setup, and keeps the test data consistent.
"""

import frappe


def ensure_item(item_code: str, stock_uom: str = "Nos") -> str:
    """Create the given sales item if it does not exist.

    Args:
        item_code: Item code to create.
        stock_uom: Stock UOM of the item.

    Returns:
        The item code.
    """
    if frappe.db.exists("Item", item_code):
        frappe.db.set_value("Item", item_code, "disabled", 0)
        frappe.db.set_value("Item", item_code, "stock_uom", stock_uom)
        return item_code

    item = frappe.new_doc("Item")
    item.item_code = item_code
    item.item_name = item_code
    item.item_group = frappe.db.get_value("Item Group", {"is_group": 0}, "name")
    item.stock_uom = stock_uom
    item.is_stock_item = 0
    item.is_fixed_asset = 0
    item.is_sales_item = 1
    item.insert(ignore_permissions=True)

    return item_code


def ensure_price_list(price_list_name: str) -> str:
    """Create the given selling price list if it does not exist.

    Args:
        price_list_name: Name of the price list.

    Returns:
        The price list name.
    """
    if frappe.db.exists("Price List", price_list_name):
        frappe.db.set_value("Price List", price_list_name, "enabled", 1)
        return price_list_name

    price_list = frappe.new_doc("Price List")
    price_list.price_list_name = price_list_name
    price_list.selling = 1
    price_list.currency = (
        frappe.db.get_single_value("Global Defaults", "default_currency")
        or frappe.db.get_value("Currency", {}, "name")
    )
    price_list.insert(ignore_permissions=True)

    return price_list_name


def ensure_property(property_name: str, service_item: str | None = None) -> str:
    """Create the given utility property if it does not exist.

    Args:
        property_name: ``Utility Property`` name.
        service_item: Service item to link, when one is required.

    Returns:
        The property name.
    """
    if frappe.db.exists("Utility Property", property_name):
        if service_item:
            frappe.db.set_value("Utility Property", property_name, "service_item", service_item)
        frappe.db.set_value("Utility Property", property_name, "status", "Occupied")
        return property_name

    property_doc = frappe.new_doc("Utility Property")
    property_doc.name = property_name
    property_doc.property_name = property_name
    property_doc.status = "Occupied"
    property_doc.company = frappe.db.get_value("Company", {}, "name")
    property_doc.is_group = 0
    property_doc.is_fixed_asset = 0
    if service_item:
        property_doc.service_item = service_item
    property_doc.flags.ignore_mandatory = True
    property_doc.flags.ignore_links = True
    property_doc.insert(ignore_permissions=True)

    return property_name


def ensure_customer(customer_name: str) -> str:
    """Create the given individual customer if it does not exist.

    Args:
        customer_name: Customer name.

    Returns:
        The customer name.
    """
    if not frappe.db.exists("Customer", customer_name):
        customer = frappe.new_doc("Customer")
        customer.customer_name = customer_name
        customer.customer_type = "Individual"
        customer.insert(ignore_permissions=True)

    return customer_name


def delete_prices(item_code: str, price_list: str) -> None:
    """Remove the Item Prices of an item in a price list.

    Args:
        item_code: Item whose prices are removed.
        price_list: Price list to clear.
    """
    frappe.db.delete("Item Price", {"item_code": item_code, "price_list": price_list})
