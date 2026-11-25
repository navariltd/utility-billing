"""Where a meter's previous reading starts after an installation, a reconnection or a takeover.

A Closed Warranty Claim installs a meter at a customer. Its Opening Reading is
the number the meter showed when the claim was closed, for example 0 after a
reset. The claim's period starts at its Resolution Date, which ERPNext stamps
when the claim is closed and clears when it leaves Closed.

The previous reading of a Meter Reading row is, in order:

1. the customer's last submitted reading of the meter dated in the claim's
   period, when the claim has an Opening Reading;
2. the claim's Opening Reading;
3. without an Opening Reading, the lookup the app always used: the last
   submitted reading of the assignment's scope when a Bill Structure
   Assignment applies, else the last invoiced reading of the customer.

The claim is the customer's Closed claim for the meter with the latest
Resolution Date (then the latest created).
"""

import frappe
from frappe import _
from frappe.utils import flt, get_datetime, getdate

CLAIM_DOCTYPE = "Warranty Claim"
OPENING_SET_FIELD = "opening_reading_set"
OPENING_FIELD = "opening_reading"

# Set to True to refuse closing such a claim instead of warning
OPENING_READING_REQUIRED = False


def has_opening_fields() -> bool:
    """Return whether Warranty Claim has the Opening Reading fields on this site."""
    return frappe.get_meta(CLAIM_DOCTYPE).has_field(OPENING_SET_FIELD)


def meter_claim(customer: str | None, meter: str | None):
    """Return the customer's Closed claim for the meter, or ``None``.

    With several, the one with the latest Resolution Date, then the latest created.
    """
    if not customer or not meter:
        return None

    fields = ["name", "resolution_date"]
    if has_opening_fields():
        fields += [OPENING_SET_FIELD, OPENING_FIELD]

    claims = frappe.get_all(
        CLAIM_DOCTYPE,
        filters={"customer": customer, "serial_no": meter, "status": "Closed"},
        fields=fields,
        order_by="resolution_date desc, creation desc",
        limit=1,
    )
    return claims[0] if claims else None


def previous_reading(reading, item):
    """Return the previous reading of a Meter Reading row and the claim it used.

    The one lookup for both billing paths, with and without a Bill Structure
    Assignment.

    Args:
        reading: ``Meter Reading`` document, its assignment already set.
        item: Its ``Meter Reading Item`` row.

    Returns:
        ``(previous_reading, claim)``; ``claim`` is ``None`` without a Closed claim.
    """
    from utility_billing.utility_billing.doctype.meter_reading.meter_reading import get_previous_invoice_reading
    from utility_billing.utility_billing.utils.structure_billing import previous_assigned_reading

    value = get_previous_invoice_reading(item_code=item.item_code, customer=reading.customer, meter_number=item.meter_number)
    if reading.get("bill_structure_assignment"):
        value = previous_assigned_reading(reading, item, value)

    claim = meter_claim(reading.customer, item.meter_number)
    if claim and claim.get(OPENING_SET_FIELD):
        since = last_reading_in_period(reading, item, claim.resolution_date)
        value = since if since is not None else flt(claim.get(OPENING_FIELD))

    return value, claim


def last_reading_in_period(reading, item, resolution_date) -> float | None:
    """Return the customer's last submitted reading of the meter since ``resolution_date``.

    Readings dated after that day, or on that day and saved after that time.
    With a Bill Structure Assignment, only those of its company and property,
    as the assignment's own lookup does. Without a Resolution Date, any.
    """
    conditions = [
        "r.docstatus = 1",
        "r.customer = %(customer)s",
        "i.item_code = %(item_code)s",
        "i.meter_number = %(meter)s",
        "r.name != %(name)s",
    ]
    values = {
        "customer": reading.customer,
        "item_code": item.item_code,
        "meter": item.meter_number,
        "name": reading.name or "",
    }
    if reading.get("bill_structure_assignment"):
        conditions += ["r.company = %(company)s", "coalesce(r.property, '') = %(property)s"]
        values.update(company=reading.company, property=reading.get("property") or "")
    if resolution_date:
        conditions.append("(r.date > %(day)s or (r.date = %(day)s and r.creation >= %(since)s))")
        values.update(day=getdate(resolution_date), since=get_datetime(resolution_date))

    rows = frappe.db.sql(
        f"""
        select i.current_reading
        from `tabMeter Reading Item` i
        inner join `tabMeter Reading` r on r.name = i.parent
        where {" and ".join(conditions)}
        order by r.date desc, r.creation desc
        limit 1
        """,
        values,
    )
    return rows[0][0] if rows else None


def check_reading_not_lower(reading, item, claim) -> None:
    """Refuse a current reading lower than the previous one, pointing to the claim's Opening Reading."""
    if item.current_reading >= item.previous_reading:
        return

    message = _("The current reading {0} in row {1} is lower than the previous reading {2}.").format(
        item.current_reading, item.idx, item.previous_reading
    )
    if claim:
        message += " " + _(
            "If meter {0} was reset or replaced, correct the Opening Reading on Warranty Claim {1}."
        ).format(item.meter_number, claim.name)
    elif item.meter_number:
        message += " " + _(
            "If meter {0} was reset or replaced, correct the Opening Reading on its Closed Warranty Claim."
        ).format(item.meter_number)
    frappe.throw(message, title=_("Reading Lower Than Previous"))


@frappe.whitelist()
def preview_previous_reading(
    customer: str,
    item_code: str,
    meter_number: str | None = None,
    company: str | None = None,
    date: str | None = None,
    property: str | None = None,
    name: str | None = None,
) -> dict:
    """Return the previous reading the save will use, for the Meter Reading form."""
    from utility_billing.utility_billing.utils.structure_billing import set_assignment_for_date

    reading = frappe.new_doc("Meter Reading")
    reading.update({"customer": customer, "company": company, "date": date, "property": property})
    if name and not name.startswith("new-"):
        reading.name = name
    set_assignment_for_date(reading)
    item = reading.append("items", {"item_code": item_code, "meter_number": meter_number})

    value, claim = previous_reading(reading, item)
    return {"previous_reading": value, "claim": claim.name if claim else None}


def check_opening_reading(doc, method=None) -> None:
    """Ask for the Opening Reading when a used meter's claim is closed.

    When the claim becomes Closed, or its serial or customer changes while
    Closed, the serial has a submitted Meter Reading and Opening Reading Set is
    not ticked. A warning, unless ``OPENING_READING_REQUIRED``.

    Args:
        doc: ``Warranty Claim`` document.
    """
    if doc.status != "Closed" or not doc.serial_no or not has_opening_fields() or doc.get(OPENING_SET_FIELD):
        return
    if not any(doc.has_value_changed(field) for field in ("status", "serial_no", "customer")):
        return
    if not meter_has_readings(doc.serial_no):
        return

    message = _(
        "Meter {0} already has Meter Readings. Tick Opening Reading Set and enter the number the meter shows now, "
        "so the first reading of this claim starts from it."
    ).format(doc.serial_no)
    if OPENING_READING_REQUIRED:
        frappe.throw(message, title=_("Opening Reading Needed"))
    frappe.msgprint(message, title=_("Opening Reading Needed"), indicator="orange")


def meter_has_readings(meter: str) -> bool:
    """Return whether any customer has a submitted Meter Reading of the meter."""
    return bool(
        frappe.db.sql(
            """
            select 1
            from `tabMeter Reading Item` i
            inner join `tabMeter Reading` r on r.name = i.parent
            where r.docstatus = 1 and i.meter_number = %s
            limit 1
            """,
            meter,
        )
    )
