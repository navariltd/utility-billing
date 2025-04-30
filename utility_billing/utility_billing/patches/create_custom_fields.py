from .create_fields_from_json import create_fields_from_json


def execute() -> None:
    create_fields_from_json("./custom_fields/bom.json", "BOM")
    
    create_fields_from_json("./custom_fields/contract.json", "Contract")
    
    create_fields_from_json("./custom_fields/customer.json", "Customer")
    
    create_fields_from_json("./custom_fields/issue.json", "Issue")
    
    create_fields_from_json("./custom_fields/item.json", "Item")
    
    create_fields_from_json("./custom_fields/item_price.json", "Item Price")
    
    create_fields_from_json("./custom_fields/sales_invoice.json", "Sales Invoice")
    
    create_fields_from_json("./custom_fields/sales_invoice_item.json", "Sales Invoice Item")
    
    create_fields_from_json("./custom_fields/sales_order.json", "Sales Order")
    
    create_fields_from_json("./custom_fields/sales_order_item.json", "Sales Order Item")
    
    create_fields_from_json("./custom_fields/auto_repeat.json", "Auto Repeat")