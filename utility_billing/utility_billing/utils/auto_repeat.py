import frappe
from frappe.query_builder import DocType
from erpnext.accounts.doctype.sales_invoice.sales_invoice import create_dunning
import frappe
from math import floor


@frappe.whitelist()
def cancel_auto_repeats_for_property(property_name: str) -> None:
    SalesInvoice = DocType("Sales Invoice")
    SalesInvoiceItem = DocType("Sales Invoice Item")
    AutoRepeat = DocType("Auto Repeat")

    invoice_query = (
        frappe.qb.from_(SalesInvoice)
        .left_join(SalesInvoiceItem)
        .on(SalesInvoice.name == SalesInvoiceItem.parent)
        .select(SalesInvoice.name)
        .where(
            (SalesInvoice.utility_property == property_name)
            | (SalesInvoiceItem.utility_property == property_name)
        )
        .distinct()
    )
    invoice_names = [row[0] for row in invoice_query.run()]
    
    if not invoice_names:
        return

    auto_repeat_query = (
        frappe.qb.from_(AutoRepeat)
        .select(AutoRepeat.name, AutoRepeat.reference_document)
        .where(
            (AutoRepeat.reference_doctype == "Sales Invoice")
            & (AutoRepeat.reference_document.isin(invoice_names))
        )
    )
    auto_repeats = auto_repeat_query.run()
    for auto_repeat in auto_repeats:
        auto_repeat_name = auto_repeat[0]
        auto_repeat_doc = frappe.get_doc("Auto Repeat", auto_repeat_name)
        auto_repeat_doc.disabled = 1
        auto_repeat_doc.save()


@frappe.whitelist()
def create_dunning_for_overdue_invoices():
    # TODO: WIP — Dunning penalty logic under development.
    # - Penalty can be:
    #     - A fixed amount (e.g., 500 KES),
    #     - A fixed percentage of outstanding (e.g., 2% one-time),
    #     - Potentially extended to other future scenarios (e.g., tiered penalties).
    # - This is **not** an annualized interest model — apply the penalty **once**, based on total outstanding after grace period.
    # - Recurring logic (if enabled) means reapplying this fixed penalty after each recurrence interval.
    # - Challenge:
    #     - Correctly track 'overdue_days' beyond grace period,
    #     - Ensure we don’t double-apply penalties,
    #     - Avoid compounding unless explicitly intended in future logic.
    # - Solution needs a mechanism to check past dunning records and calculate new penalties accurately.

    settings = frappe.get_doc("Utility Billing Settings", "Utility Billing Settings")

    if not settings.apply_penalty:
        return

    grace_days = settings.penalty_grace_days or 0
    recurrence_days = settings.recurrence_interval_days or 0
    max_penalty = settings.max_penalty_amount or 0
    today = frappe.utils.nowdate()

    overdue_invoices = frappe.get_all("Sales Invoice",
        filters={
            "docstatus": 1,
            "outstanding_amount": [">", 0],
            "due_date": ["<", today]
        },
        fields=["name", "due_date", "customer", "outstanding_amount"]
    )

    for inv in overdue_invoices:
        due_date = frappe.utils.getdate(inv.due_date)
        overdue_days = (frappe.utils.getdate(today) - due_date).days

        if overdue_days <= grace_days:
            continue  # Still within grace period

        penalty_count = 1
        if settings.recurring_penalty and recurrence_days > 0:
            penalty_count = floor((overdue_days - grace_days) / recurrence_days)

        total_penalty = 0.0
        for _ in range(penalty_count):
            if settings.penalty_type == "Percentage":
                if settings.recurring_penalty:
                    penalty = (settings.penalty_value / 100) * inv.outstanding_amount
                else:
                    # Convert annual percentage to overdue-day equivalent
                    annual_percentage = settings.penalty_value
                    penalty = (annual_percentage / 100) * inv.outstanding_amount * (overdue_days / 365)
            else:  # Fixed Amount
                if settings.recurring_penalty:
                    penalty = settings.penalty_value
                else:
                    # Convert fixed amount to equivalent percentage of outstanding
                    annual_interest_rate = (settings.penalty_value / inv.outstanding_amount) * (365 / overdue_days) * 100 if overdue_days > 0 else 0
                    penalty = (annual_interest_rate / 100) * inv.outstanding_amount * (overdue_days / 365)

            total_penalty += penalty

        if max_penalty > 0:
            total_penalty = min(total_penalty, max_penalty)

        # Avoid duplicate penalties
        if frappe.db.exists("Dunning", {
            "reference_doctype": "Sales Invoice",
            "reference_name": inv.name,
            "posting_date": today
        }):
            continue

        # Create Dunning
        dunning = create_dunning(inv.name, ignore_permissions=True)

        # Update dunning line
        for line in dunning.overdue_payments:
            if line.sales_invoice == inv.name:
                line.overdue_days = overdue_days
                line.interest = round(total_penalty, 2)

        dunning.save(ignore_permissions=True)

