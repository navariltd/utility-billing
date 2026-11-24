"""Disconnecting a customer's meters.

A Closed Warranty Claim means the meter is installed at the customer. A
disconnection request is a Utility Service Request for a customer whose Request
Type is the Disconnection Request Type in Utility Billing Settings. Once it is
submitted, staff pick the claims to disconnect: each is set back to Open, which
takes the meter back, and the Auto Repeats staff tick are turned off. The
customer's Status becomes Disconnected when none of its claims stays Closed.

The Status is the Custom Field ``custom_status`` on Customer, which only some
sites have. Without it, nothing reads or writes a Status.
"""

import json

import frappe
from frappe import _
from frappe.query_builder import DocType
from frappe.utils import getdate

SETTINGS = "Utility Billing Settings"
REQUEST_DOCTYPE = "Utility Service Request"
STATUS_FIELD = "custom_status"
DISCONNECTED = "Disconnected"
CLAIM_DOCTYPE = "Warranty Claim"
DISCONNECTION_FIELD = "disconnection_request"


def has_status_field() -> bool:
    """Return whether Customer has the Status field on this site."""
    return frappe.get_meta("Customer").has_field(STATUS_FIELD)


def customer_status(customer: str | None) -> str | None:
    """Return the customer's Status, or ``None`` without a customer or a Status field."""
    if not customer or not has_status_field():
        return None
    return frappe.db.get_value("Customer", customer, STATUS_FIELD)


def is_disconnection_request(doc) -> bool:
    """Return whether a request's Request Type is the Disconnection Request Type."""
    # Read only once the site is migrated: until then the setting does not exist
    if not frappe.get_meta(SETTINGS).has_field("disconnection_request_type"):
        return False

    request_type = frappe.db.get_single_value(SETTINGS, "disconnection_request_type")
    return bool(request_type and doc.get("request_type") == request_type)


def closed_claims(customer: str) -> list[dict]:
    """Return the customer's Closed claims with a serial number, oldest first."""
    return frappe.get_all(
        CLAIM_DOCTYPE,
        filters={"customer": customer, "status": "Closed", "serial_no": ("is", "set")},
        fields=["name", "serial_no", "utility_property", "utility_service_request"],
        order_by="creation",
    )


def request_properties(request) -> set[str]:
    """Return the request's own property and those of its property rows."""
    properties = {row.utility_property for row in request.get("requested_properties") or [] if row.utility_property}
    if request.get("utility_property"):
        properties.add(request.utility_property)
    return properties


def claims_for_request(request) -> list[dict]:
    """Return the customer's Closed claims the request may disconnect.

    Those on the request's properties when any match, otherwise all of them.
    """
    claims = closed_claims(request.customer)
    properties = request_properties(request)
    matching = [claim for claim in claims if claim.utility_property in properties]
    return matching or claims


def customer_auto_repeats(customer: str) -> list[dict]:
    """Return the customer's enabled Auto Repeats.

    An Auto Repeat belongs to the customer of its reference document (the Sales
    Order or Sales Invoice it copies).
    """
    auto_repeat = DocType("Auto Repeat")
    rows = []
    for doctype in frappe.get_all("Auto Repeat", filters={"disabled": 0}, distinct=True, pluck="reference_doctype"):
        if not doctype or not frappe.get_meta(doctype).has_field("customer"):
            continue

        reference = DocType(doctype)
        rows += (
            frappe.qb.from_(auto_repeat)
            .join(reference)
            .on(reference.name == auto_repeat.reference_document)
            .select(
                auto_repeat.name,
                auto_repeat.reference_doctype,
                auto_repeat.reference_document,
                auto_repeat.frequency,
            )
            .where(auto_repeat.reference_doctype == doctype)
            .where(auto_repeat.disabled == 0)
            .where(reference.customer == customer)
            .run(as_dict=True)
        )
    return sorted(rows, key=lambda row: row.name)


def meters_without_final_reading(customer: str, date) -> list[str]:
    """Return the customer's meters with no submitted Meter Reading on or after ``date``.

    The customer's meters are the serial numbers on its Closed Warranty Claims.
    """
    meters = {claim.serial_no for claim in closed_claims(customer)}
    if not meters:
        return []

    reading = DocType("Meter Reading")
    row = DocType("Meter Reading Item")
    read = (
        frappe.qb.from_(row)
        .join(reading)
        .on(reading.name == row.parent)
        .select(row.meter_number)
        .distinct()
        .where(row.parenttype == "Meter Reading")
        .where(reading.docstatus == 1)
        .where(reading.customer == customer)
        .where(reading.date >= date)
        .where(row.meter_number.isin(list(meters)))
        .run(pluck=True)
    )
    return sorted(meters - set(read))


def request_date(request):
    """Return the request's Date, or the day it was created when Date is blank."""
    return getdate(request.get("date") or request.creation)


def disconnectable_request(name: str):
    """Return the submitted disconnection request with a customer, or ``None``."""
    request = frappe.get_doc(REQUEST_DOCTYPE, name)
    request.check_permission("read")
    if request.docstatus != 1 or not request.get("customer") or not is_disconnection_request(request):
        return None
    return request


@frappe.whitelist()
def disconnect_options(request: str) -> dict | None:
    """Return what the Disconnect Meter dialog lists, or ``None`` when it is not offered.

    Offered on a submitted disconnection request with a customer, while the
    customer still has a Closed claim.

    Args:
        request: ``Utility Service Request`` name.

    Returns:
        ``{"claims": [...], "auto_repeats": [...]}``. Each claim carries
        ``no_final_reading`` and ``selected``; each Auto Repeat ``selected``.
    """
    doc = disconnectable_request(request)
    if not doc:
        return None

    claims = claims_for_request(doc)
    if not claims:
        return None

    date = request_date(doc)
    unread = set(meters_without_final_reading(doc.customer, date))
    for claim in claims:
        claim.no_final_reading = claim.serial_no in unread
        claim.selected = len(claims) == 1

    # Auto Repeats cannot be traced to a meter, so they are only preselected
    # when the customer has a single connection
    single = len(closed_claims(doc.customer)) == 1
    auto_repeats = customer_auto_repeats(doc.customer)
    for row in auto_repeats:
        row.selected = single

    return {"customer": doc.customer, "date": date, "claims": claims, "auto_repeats": auto_repeats}


@frappe.whitelist(methods=["POST"])
def disconnect_meters(request: str, claims: str | list, auto_repeats: str | list | None = None) -> dict:
    """Disconnect the chosen meters of a disconnection request.

    Each claim is set back to Open with the request in Disconnection Request,
    and each Auto Repeat is turned off, all with a Comment. The customer's
    Status becomes Disconnected when none of its claims stays Closed. Any
    error undoes the whole call.

    Args:
        request: ``Utility Service Request`` name.
        claims: Names of the customer's Closed Warranty Claims.
        auto_repeats: Names of the customer's enabled Auto Repeats.

    Returns:
        ``{"claims": [...], "auto_repeats": [...], "status": ...}``: what changed.
    """
    claims = parse_names(claims)
    auto_repeats = parse_names(auto_repeats)

    doc = disconnectable_request(request)
    if not doc:
        frappe.throw(_("Utility Service Request {0} is not a submitted disconnection request with a customer.").format(request))
    if not claims:
        frappe.throw(_("Select at least one Warranty Claim."))

    allowed_claims = {claim.name for claim in closed_claims(doc.customer)}
    if refused := [name for name in claims if name not in allowed_claims]:
        frappe.throw(
            _("These Warranty Claims are not Closed claims of customer {0}: {1}.").format(doc.customer, ", ".join(refused))
        )

    allowed_repeats = {row.name for row in customer_auto_repeats(doc.customer)}
    if refused := [name for name in auto_repeats if name not in allowed_repeats]:
        frappe.throw(
            _("These Auto Repeats are not enabled Auto Repeats of customer {0}: {1}.").format(doc.customer, ", ".join(refused))
        )

    claim_docs = [frappe.get_doc(CLAIM_DOCTYPE, name) for name in claims]
    repeat_docs = [frappe.get_doc("Auto Repeat", name) for name in auto_repeats]
    for each in claim_docs + repeat_docs:
        each.check_permission("write")

    for claim in claim_docs:
        claim.status = "Open"
        claim.set(DISCONNECTION_FIELD, doc.name)
        claim.save()
        add_comment(
            CLAIM_DOCTYPE,
            claim.name,
            _("Meter {0} disconnected by Utility Service Request {1}: the claim is Open again.").format(
                claim.serial_no, doc.name
            ),
        )

    for repeat in repeat_docs:
        frappe.db.set_value("Auto Repeat", repeat.name, {"disabled": 1, "status": "Disabled"})
        add_comment(
            "Auto Repeat", repeat.name, _("Turned off by disconnection request {0} of customer {1}.").format(doc.name, doc.customer)
        )

    status = None
    if not closed_claims(doc.customer) and set_disconnected(doc.customer, doc.name):
        status = DISCONNECTED

    return {"claims": claims, "auto_repeats": auto_repeats, "status": status}


def parse_names(value) -> list[str]:
    if isinstance(value, str):
        value = json.loads(value) if value.startswith("[") else [value]
    return list(dict.fromkeys(name for name in value or [] if name))


def set_disconnected(customer: str, request: str) -> bool:
    """Set the customer's Status to Disconnected, without saving the customer.

    Returns:
        Whether the Status was set: not on a site without the field.
    """
    if not has_status_field():
        return False

    frappe.db.set_value("Customer", customer, STATUS_FIELD, DISCONNECTED)
    add_comment("Customer", customer, _("Status set to Disconnected by Utility Service Request {0}.").format(request))
    return True


def check_reading_customer(doc) -> None:
    """Refuse a Meter Reading for a Disconnected customer.

    Args:
        doc: ``Meter Reading`` document.
    """
    if customer_status(doc.get("customer")) == DISCONNECTED:
        frappe.throw(
            _(
                "Customer {0} is Disconnected: its meters were taken back, so no Meter Reading can be saved for it. "
                "If the customer is reconnected, close the meter's Warranty Claim again and set the customer's "
                "Status back to Active."
            ).format(doc.customer),
            title=_("Customer Disconnected"),
        )


def add_comment(doctype: str, name: str, content: str) -> None:
    frappe.get_doc(
        {
            "doctype": "Comment",
            "comment_type": "Comment",
            "reference_doctype": doctype,
            "reference_name": name,
            "content": content,
        }
    ).insert(ignore_permissions=True)
