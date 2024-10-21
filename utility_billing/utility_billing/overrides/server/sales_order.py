import json
from datetime import datetime

import frappe
from erpnext.accounts.party import get_party_account
from erpnext.setup.doctype.item_group.item_group import get_item_group_defaults
from erpnext.stock.doctype.item.item import get_item_defaults
from frappe import _
from frappe.contacts.doctype.address.address import get_company_address
from frappe.model.mapper import get_mapped_doc
from frappe.model.utils import get_fetch_values
from frappe.utils import flt, today


def create_log(
    doc_name, e, from_doctype, to_doctype, status, log_date=None, restarted=0
):
    transaction_log = frappe.new_doc("Bulk Transaction Log Detail")
    transaction_log.transaction_name = doc_name
    transaction_log.date = today()
    now = datetime.now()
    transaction_log.time = now.strftime("%H:%M:%S")
    transaction_log.transaction_status = status
    transaction_log.error_description = str(e)
    transaction_log.from_doctype = from_doctype
    transaction_log.to_doctype = to_doctype
    transaction_log.retried = restarted
    transaction_log.save(ignore_permissions=True)


@frappe.whitelist()
def enqueue_sales_invoice_creation(source_names):
    """Enqueue Sales Invoice creation for background processing."""
    if isinstance(source_names, str):
        source_names = json.loads(source_names)

    if not isinstance(source_names, (list, tuple)):
        raise ValueError(
            _(
                "Invalid input type for source_names. Expected JSON array, list, or tuple."
            )
        )

    orders_by_customer = get_unique_customers_and_orders(source_names)
    num_customers = len(orders_by_customer)

    frappe.enqueue(
        create_sales_invoices_in_background,
        source_names=source_names,
        queue="long",
        timeout=3000,
        job_name="Create Sales Invoices",
    )

    return _(
        "Started a background job to create Sales Invoice for {0} customers."
    ).format(num_customers)


@frappe.whitelist()
def create_sales_invoices_in_background(source_names):
    """Create Sales Invoices in the background."""
    orders_by_customer = get_unique_customers_and_orders(source_names)

    for customer, orders in orders_by_customer.items():
        try:
            make_sales_invoice(orders)
            for order in orders:
                create_log(order, None, "Sales Order", "Sales Invoice", "Success")
            frappe.msgprint(
                _("Successfully created Sales Invoice for customer: {0}").format(
                    customer
                )
            )
        except Exception as e:
            for order in orders:
                create_log(order, e, "Sales Order", "Sales Invoice", "Failed")
            frappe.log_error(
                f"Error creating Sales Invoice for customer {customer}, {e}"
            )
            frappe.msgprint(
                _("Error creating Sales Invoice for customer {0}: {1}").format(
                    customer, e
                )
            )
            continue


@frappe.whitelist()
def get_unique_customers_and_orders(source_names):
    """Return a dictionary of customers with their respective sales orders."""
    if isinstance(source_names, str):
        source_names = json.loads(source_names)

    if not isinstance(source_names, (list, tuple)):
        raise ValueError(
            _(
                "Invalid input type for source_names. Expected JSON array, list, or tuple."
            )
        )

    orders_by_customer = {}

    for source_name in source_names:
        sales_order = frappe.get_doc("Sales Order", source_name)
        customer = sales_order.customer

        if customer not in orders_by_customer:
            orders_by_customer[customer] = []

        orders_by_customer[customer].append(source_name)

    return orders_by_customer


@frappe.whitelist()
def make_sales_invoice(source_names, target_doc=None, ignore_permissions=False):
    """Create Sales Invoice from Sales Orders."""
    if isinstance(source_names, str):
        source_names = json.loads(source_names)

    if not isinstance(source_names, (list, tuple)):
        raise ValueError(
            _(
                "Invalid input type for source_names. Expected JSON array, list, or tuple."
            )
        )

    def postprocess(source, target):
        set_missing_values(source, target)
        if target.get("allocate_advances_automatically"):
            target.set_advances()

    def set_missing_values(source, target):
        target.flags.ignore_permissions = True
        target.run_method("set_missing_values")
        target.run_method("set_po_nos")
        target.run_method("calculate_taxes_and_totals")
        target.run_method("set_use_serial_batch_fields")

        if source.company_address:
            target.update({"company_address": source.company_address})
        else:
            target.update(get_company_address(target.company))

        if target.company_address:
            target.update(
                get_fetch_values(
                    "Sales Invoice", "company_address", target.company_address
                )
            )

        if source.loyalty_points and source.order_type == "Shopping Cart":
            target.redeem_loyalty_points = 1
            target.loyalty_points = source.loyalty_points

        target.debit_to = get_party_account("Customer", source.customer, source.company)

    def update_item(source, target, source_parent):
        """Update the item information for the invoice."""
        target.amount = flt(source.amount) - flt(source.billed_amt)
        target.base_amount = target.amount * flt(source_parent.conversion_rate)
        target.qty = (
            target.amount / flt(source.rate)
            if (source.rate and source.billed_amt)
            else source.qty - source.returned_qty
        )

        if source_parent.project:
            target.cost_center = frappe.db.get_value(
                "Project", source_parent.project, "cost_center"
            )
        if target.item_code:
            item = get_item_defaults(target.item_code, source_parent.company)
            item_group = get_item_group_defaults(
                target.item_code, source_parent.company
            )
            cost_center = item.get("selling_cost_center") or item_group.get(
                "selling_cost_center"
            )

            if cost_center:
                target.cost_center = cost_center

    doclist = []

    for source_name in source_names:
        try:
            current_doc = get_mapped_doc(
                "Sales Order",
                source_name,
                {
                    "Sales Order": {
                        "doctype": "Sales Invoice",
                        "field_map": {
                            "party_account_currency": "party_account_currency",
                            "payment_terms_template": "payment_terms_template",
                        },
                        "field_no_map": ["payment_terms_template"],
                        "validation": {"docstatus": ["=", 1]},
                    },
                    "Sales Order Item": {
                        "doctype": "Sales Invoice Item",
                        "field_map": {
                            "name": "so_detail",
                            "parent": "sales_order",
                        },
                        "postprocess": update_item,
                        "condition": lambda doc: doc.qty
                        and (
                            doc.base_amount == 0
                            or abs(doc.billed_amt) < abs(doc.amount)
                        ),
                    },
                    "Sales Taxes and Charges": {
                        "doctype": "Sales Taxes and Charges",
                        "reset_value": True,
                    },
                    "Sales Team": {"doctype": "Sales Team", "add_if_empty": True},
                },
                target_doc,
                postprocess,
                ignore_permissions=ignore_permissions,
            )

            doclist.append(current_doc)

        except Exception as e:
            frappe.log_error(
                message=str(e), title=f"Error processing Sales Order {source_name}"
            )
            create_log(source_name, e, "Sales Order", "Sales Invoice", "Failed")
            continue

    if doclist:
        target_invoice = doclist[0]
        for doc in doclist[1:]:
            merge_invoice_items(target_invoice, doc)
            merge_invoice_taxes(target_invoice, doc)

        target_invoice.run_method("calculate_taxes_and_totals")
        target_invoice.run_method("set_payment_schedule")

    target_invoice.save()

    return target_invoice


def merge_invoice_items(target_invoice, doc):
    """Merge items from multiple docs into a single invoice."""
    for item in doc.items:
        existing_item = next(
            (i for i in target_invoice.items if i.item_code == item.item_code), None
        )
        if existing_item:
            existing_item.qty += item.qty
            existing_item.amount += item.amount
            existing_item.base_amount += item.base_amount
        else:
            target_invoice.append("items", item)


def merge_invoice_taxes(target_invoice, doc):
    """Merge taxes from multiple docs into a single invoice."""
    for tax in doc.taxes:
        existing_tax = next(
            (t for t in target_invoice.taxes if t.account_head == tax.account_head),
            None,
        )
        if existing_tax:
            existing_tax.tax_amount += tax.tax_amount
        else:
            target_invoice.append("taxes", tax)
