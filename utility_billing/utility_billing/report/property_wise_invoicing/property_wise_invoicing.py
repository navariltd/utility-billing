# Copyright (c) 2026, Navari Ltd and contributors
# For license information, please see license.txt

"""Invoiced amounts of each primary utility property, month by month.

Amounts come from the Sales Invoice lines billing a property's own service item,
dated by their Deferred Posting Date, never from invoice totals: one invoice can
bill several months and several properties. Every month a submitted lease was
active up to today gets a row, at zero when nothing was invoiced, so billing
gaps show up. Lines billed outside any lease are kept, so the totals match the
ledger.
"""

from collections import defaultdict
from datetime import date

import frappe
from frappe import _
from frappe.query_builder import functions as fn
from frappe.utils import add_months, flt, get_first_day, get_last_day, getdate, today

from utility_billing.utility_billing.utils.item_price_scope import property_contract_period

REQUEST_DOCTYPE = "Utility Service Request"
LEASE_DOCTYPE = "Contract Utility Property Item"


def execute(filters=None):
    filters = frappe._dict(filters or {})
    period_start, period_end = get_period(filters)

    leases = get_leases(filters)
    properties = get_properties()
    owners = get_service_item_owners(properties)

    # Zero rows stop at the current month, lease ends cover the whole period
    grid = build_lease_grid(leases, period_start, period_end, getdate(today()))
    lease_ends = build_lease_grid(leases, period_start, period_end, period_end)
    invoiced = resolve_lines(get_invoiced_lines(filters, period_start, period_end, owners), owners, leases)

    rows = merge(grid, invoiced, lease_ends)
    if filters.property:
        rows = [row for row in rows if row.property == filters.property]

    return get_columns(), add_totals(rows)


def get_columns() -> list[dict]:
    return [
        {"label": _("Property"), "fieldname": "property", "fieldtype": "Link", "options": "Utility Property", "width": 180},
        {"label": _("Customer"), "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 180},
        {"label": _("Month"), "fieldname": "month", "fieldtype": "Data", "width": 110},
        {"label": _("Invoiced Amount"), "fieldname": "invoiced_amount", "fieldtype": "Currency", "width": 150},
        {"label": _("Lease Expires"), "fieldname": "lease_expires", "fieldtype": "Date", "width": 120},
    ]


def get_period(filters) -> tuple[date, date]:
    """Return the first and last day covered by the Year and Month filters."""
    if not filters.get("year"):
        frappe.throw(_("Year is required"))

    year = int(filters.year)
    if filters.get("month"):
        start = date(year, int(filters.month), 1)
        return start, getdate(get_last_day(start))

    return date(year, 1, 1), date(year, 12, 31)


def get_leases(filters) -> list[frappe._dict]:
    """Return every active property lease of the submitted requests.

    The dates come from ``property_contract_period``: the row's own dates,
    falling back to the request's.
    """
    lease = frappe.qb.DocType(LEASE_DOCTYPE)
    request = frappe.qb.DocType(REQUEST_DOCTYPE)
    query = (
        frappe.qb.from_(lease)
        .join(request)
        .on(request.name == lease.parent)
        .select(lease.parent, lease.utility_property, request.customer)
        .where(lease.parenttype == REQUEST_DOCTYPE)
        .where(lease.is_active == 1)
        .where(lease.utility_property.isnotnull())
        .where(request.docstatus == 1)
        .distinct()
    )
    if filters.get("company"):
        query = query.where(request.company == filters.company)
    if filters.get("customer"):
        query = query.where(request.customer == filters.customer)

    leases = []
    for row in query.run(as_dict=True):
        service_request = frappe.get_doc(REQUEST_DOCTYPE, row.parent)
        start, end = property_contract_period(service_request, row.utility_property)
        leases.append(
            frappe._dict(
                service_request=row.parent,
                property=row.utility_property,
                customer=row.customer,
                start=getdate(start) if start else None,
                end=getdate(end) if end else None,
            )
        )

    return leases


def get_properties() -> dict[str, frappe._dict]:
    """Return the leaf properties with their service item."""
    return {
        row.name: row
        for row in frappe.get_all(
            "Utility Property",
            filters={"is_group": 0},
            fields=["name", "service_item"],
        )
    }


def get_service_item_owners(properties: dict) -> dict[str, list[str]]:
    """Return the properties owning each service item."""
    owners = defaultdict(list)
    for row in properties.values():
        if row.service_item:
            owners[row.service_item].append(row.name)

    return dict(owners)


def get_invoiced_lines(filters, period_start: date, period_end: date, owners: dict) -> list[frappe._dict]:
    """Return the submitted invoice lines billing a service item in the period.

    Lines are summed per item, customer, request and Deferred Posting Date. A
    line without that date falls back to the invoice Posting Date.
    """
    if not owners:
        return []

    invoice = frappe.qb.DocType("Sales Invoice")
    line = frappe.qb.DocType("Sales Invoice Item")
    billing_date = fn.Coalesce(line.custom_posting_date, invoice.posting_date)
    query = (
        frappe.qb.from_(line)
        .join(invoice)
        .on(invoice.name == line.parent)
        .select(
            line.item_code,
            invoice.customer,
            invoice.utility_service_request.as_("service_request"),
            billing_date.as_("billing_date"),
            fn.Sum(line.base_net_amount).as_("amount"),
        )
        .where(invoice.docstatus == 1)
        .where(line.item_code.isin(list(owners)))
        .where(billing_date[period_start:period_end])
        .groupby(line.item_code, invoice.customer, invoice.utility_service_request, billing_date)
    )
    if filters.get("company"):
        query = query.where(invoice.company == filters.company)
    if filters.get("customer"):
        query = query.where(invoice.customer == filters.customer)

    return query.run(as_dict=True)


def build_lease_grid(leases: list, period_start: date, period_end: date, current_date: date) -> dict:
    """Return the lease end of every property, customer and month to report.

    A month is reported when a lease overlaps it, within the period, and no
    later than the month of ``current_date``: a month still to come cannot have
    a billing gap yet. A lease without an end date runs until that limit.

    Returns:
        ``{(property, customer, first day of month): lease end}``; the latest
        end wins when two leases of the same customer cover a month, ``None``
        meaning open ended.
    """
    last_month = min(get_first_day(period_end), get_first_day(current_date))
    grid = {}

    for lease in leases:
        if not lease.start:
            continue

        month = max(get_first_day(lease.start), get_first_day(period_start))
        last = last_month if not lease.end else min(last_month, get_first_day(lease.end))

        while month <= last:
            key = (lease.property, lease.customer, month)
            grid[key] = later_end(grid[key], lease.end) if key in grid else lease.end
            month = getdate(add_months(month, 1))

    return grid


def later_end(first, second):
    """Return the later of two lease ends, ``None`` being open ended."""
    if first is None or second is None:
        return None

    return max(first, second)


def resolve_property(line, owners: dict, leases: list) -> str | None:
    """Return the property an invoice line bills, or ``None`` when ambiguous.

    An item owned by a single property bills that property. A shared item bills
    the property of the invoice's request that owns it, else the one whose lease
    for the invoice's customer covers the billing date.
    """
    candidates = owners.get(line.item_code) or []
    if len(candidates) == 1:
        return candidates[0]

    if line.service_request:
        on_request = {
            lease.property
            for lease in leases
            if lease.service_request == line.service_request and lease.property in candidates
        }
        if len(on_request) == 1:
            return on_request.pop()

    billing_date = getdate(line.billing_date)
    covering = {
        lease.property
        for lease in leases
        if lease.property in candidates
        and lease.customer == line.customer
        and lease.start
        and lease.start <= billing_date
        and (not lease.end or billing_date <= lease.end)
    }
    if len(covering) == 1:
        return covering.pop()

    return None


def resolve_lines(lines: list, owners: dict, leases: list) -> dict:
    """Sum the invoice lines per property, customer and month.

    Returns:
        ``{(property, customer, first day of month): amount}``, with an
        unresolved shared item reported under ``Unresolved (<item>)``.
    """
    invoiced = defaultdict(float)
    for line in lines:
        property_name = resolve_property(line, owners, leases) or unresolved_label(line.item_code)
        invoiced[(property_name, line.customer, get_first_day(line.billing_date))] += flt(line.amount)

    return dict(invoiced)


def merge(grid: dict, invoiced: dict, lease_ends: dict) -> list[frappe._dict]:
    """Join the invoiced amounts onto the lease grid.

    Leased months without an invoice show zero. Every row takes its lease end
    from ``lease_ends``, which also covers months after the current one, so an
    invoiced month outside any lease is the only one shown without a lease end.
    """
    rows = []
    for key in set(grid) | set(invoiced):
        property_name, customer, month = key
        rows.append(
            frappe._dict(
                property=property_name,
                customer=customer,
                month_start=month,
                month=month.strftime("%b %Y"),
                invoiced_amount=invoiced.get(key, 0.0),
                lease_expires=lease_ends.get(key),
            )
        )

    rows.sort(key=lambda row: (is_unresolved(row.property), row.property, row.month_start, row.customer or ""))
    return rows


def unresolved_label(item_code: str) -> str:
    """Return the row label of a shared item no property could be matched to."""
    return f"{_('Unresolved')} ({item_code})"


def is_unresolved(property_name: str) -> bool:
    return property_name.startswith(f"{_('Unresolved')} (")


def add_totals(rows: list) -> list[frappe._dict]:
    """Append a subtotal after each property and a grand total at the end."""
    data = []
    subtotal = grand_total = 0.0

    for index, row in enumerate(rows):
        data.append(row)
        subtotal += row.invoiced_amount
        grand_total += row.invoiced_amount

        if index + 1 == len(rows) or rows[index + 1].property != row.property:
            data.append(total_row(_("Total {0}").format(row.property), subtotal))
            subtotal = 0.0

    if rows:
        data.append(total_row(_("Grand Total"), grand_total))

    return data


def total_row(label: str, amount: float) -> frappe._dict:
    return frappe._dict(property=label, invoiced_amount=amount, is_total_row=1)
