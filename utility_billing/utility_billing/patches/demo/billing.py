import json
import frappe
from typing import List, Dict, Any
from .utils import safe_insert_doc, safe_load_json
from .company import COMPANY_NAME
from dateutil.relativedelta import relativedelta
from datetime import datetime


def insert_price_lists(price_lists: List[str]) -> None:
    for price_list in price_lists:
        safe_insert_doc(
            "Price List",
            {
                "doctype": "Price List",
                "price_list_name": price_list,
                "selling": 1,
                "currency": "KES",
                "enabled": 1,
            },
            unique_key="price_list_name"
        )

def insert_items(items: List[str]) -> None:
    for item in items:
        safe_insert_doc(
            "Item",
            {
                "doctype": "Item",
                "item_code": item,
                "item_name": item,
                "stock_uom": "Unit",
                "is_stock_item": 0,
                "is_sales_item": 1,
                "is_utility_item": 1,
                "item_group": "All Item Groups",
                "disabled": 0,
            },
            unique_key="item_code"
        )
        
def insert_tariff_blocks(blocks: List[Dict[str, Any]]) -> None:
    for block in blocks:
        safe_insert_doc(
            "Utility Tariff Block",
            {
                "doctype": "Utility Tariff Block",
                "name": block,
            },
            unique_key="name"
        )

def insert_tariff_prices(prices: List[Dict[str, Any]]) -> None:
    
    valid_from = datetime.now().date() - relativedelta(months=1)
    
    for price_item in prices:
        item_price_name = frappe.db.get_value("Item Price", 
            filters={
                "item_code": price_item["item_code"],
                "price_list": price_item.get("price_list", "Standard Selling"),
                "uom": price_item["uom"]
            },
            fieldname="name"
        )

        item_price_data = {
            "doctype": "Item Price",
            "item_code": price_item["item_code"],
            "price_list": price_item.get("price_list", "Standard Selling"),
            "price_list_rate": price_item["rate"],
            "uom": price_item["uom"],
            "currency": "KES",
            "valid_from": valid_from
        }

        if item_price_name:
            for field, value in item_price_data.items():
                if field != "doctype":
                    frappe.db.set_value("Item Price", item_price_name, field, value)
            item_price = frappe.get_doc("Item Price", item_price_name)
        else:
            item_price = frappe.get_doc(item_price_data)
            item_price.insert()

        if price_item.get("tariffs"):
            frappe.db.delete("Item Price Tariff", {"parent": item_price.name})
            
            for tariff in price_item["tariffs"]:
                tariff_data = {
                    "doctype": "Item Price Tariff",
                    "parent": item_price.name,
                    "parenttype": "Item Price",
                    "parentfield": "tariffs",
                    "block": tariff["block"],
                    "lower_limit": tariff["lower_limit"],
                    "upper_limit": tariff["upper_limit"],
                    "rate": tariff["rate"]
                }
                tariff_doc = frappe.get_doc(tariff_data)
                tariff_doc.insert()



def insert_meter_readings(readings: List[Dict[str, Any]]) -> None:
    for entry in readings:
        meter_reading_name = frappe.db.get_value("Meter Reading",
            filters={
                "customer": entry["customer"],
                "date": entry["date"],
                "property": entry["property"]
            },
            fieldname="name"
        )

        if meter_reading_name:
            doc = frappe.get_doc("Meter Reading", meter_reading_name)
            doc.update({
                "price_list": entry["price_list"],
                "currency": entry["currency"],
                "company": COMPANY_NAME
            })
        else:
            doc = frappe.get_doc({
                "doctype": "Meter Reading",
                "customer": entry["customer"],
                "date": entry["date"],
                "price_list": entry["price_list"],
                "currency": entry["currency"],
                "property": entry["property"],
                "company": COMPANY_NAME
            })

        doc.set("items", [])
        
        for item in entry.get("items", []):
            doc.append("items", {
                "item_code": item["item_code"],
                "current_reading": item["current_reading"],
                "previous_reading": item["previous_reading"],
                "consumption": item["consumption"],
                "meter_number": item["meter_number"]
            })

        doc.save()
        doc.submit()
            
            
def create_serial_numbers_and_warranty_claims(data: Dict[str, Any]) -> None:
    """Create Serial No and Warranty Claim records from JSON data.

    Args:
        data (dict): Dictionary containing serial numbers and warranty claims.
    """

    serial_numbers = data.get("serial_numbers", [])
    warranty_claims = data.get("warranty_claims", [])

    for serial_no in serial_numbers:
        safe_insert_doc(
            "Serial No",
            {
                "doctype": "Serial No",
                "serial_no": serial_no,
                "item_code": "Meter",  
                "status": "Active",
            },
            unique_key="serial_no"
        )

    for claim in warranty_claims:
        serial_no = claim.get("serial_no")
        customer = claim.get("customer")

        if not frappe.db.exists("Serial No", serial_no):
            frappe.throw(f"Serial No {serial_no} not found. Ensure it is created before creating warranty claims.")

        safe_insert_doc(
            "Warranty Claim",
            {
                "doctype": "Warranty Claim",
                "serial_no": serial_no,
                "status": claim.get("status", "Open"),
                "complaint_date": claim.get("complaint_date"),
                "customer": customer,
                "complaint": claim.get("complaint"),
            },
            unique_key=None  
        )


def billing_setup():
    tariff_data = safe_load_json("tariff.json")
    reading_data = safe_load_json("meter_reading.json")
    meter_data = safe_load_json("meter.json")  

    insert_price_lists(tariff_data["price_lists"])
    insert_items(tariff_data["items"])
    insert_tariff_blocks(tariff_data["blocks"])
    insert_tariff_prices(tariff_data["prices"])
    create_serial_numbers_and_warranty_claims(meter_data)
    insert_meter_readings(reading_data)
