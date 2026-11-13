"""The Utility Service Request link on Warranty Claims and Meter Readings.

The link is optional. A request picked by hand must belong to the claim's or
reading's customer. A reading takes its request from the Closed claims of its
meters, only when every meter row's claims point to one request; it is never
guessed from the customer alone.
"""

import frappe
from frappe import _
from frappe.utils import today

from utility_billing.utility_billing.utils.utility_item_classifier import USR_DOCTYPE, USR_PROPERTY_DOCTYPE

REQUEST_FIELD = "utility_service_request"
CLAIM_DOCTYPE = "Warranty Claim"


def check_request_customer(doc) -> None:
    """Refuse a request that does not belong to the document's customer.

    Args:
        doc: ``Warranty Claim`` or ``Meter Reading`` document.
    """
    request = doc.get(REQUEST_FIELD)
    if not request:
        return

    if frappe.db.get_value(USR_DOCTYPE, request, "customer") != doc.get("customer"):
        frappe.throw(
            _("Utility Service Request {0} does not belong to customer {1}.").format(request, doc.get("customer")),
            title=_("Wrong Utility Service Request"),
        )


def check_meters_of_customer(doc) -> None:
    """Refuse a reading whose meters are not on a Closed Warranty Claim of its customer.

    Rows without a meter are left as they are.

    Args:
        doc: ``Meter Reading`` document.
    """
    for row in doc.items:
        if row.meter_number and not frappe.db.exists(
            CLAIM_DOCTYPE, {"customer": doc.customer, "serial_no": row.meter_number, "status": "Closed"}
        ):
            frappe.throw(
                _("Meter {0} in row {1} is not on a Closed Warranty Claim of customer {2}.").format(
                    row.meter_number, row.idx, doc.customer
                ),
                title=_("Meter of Another Customer"),
            )


def request_from_claims(doc) -> str | None:
    """Return the request every meter row's Closed claims point to, or ``None``.

    ``None`` when a row has no meter, a claim has no request, or the claims
    point to different requests.

    Args:
        doc: ``Meter Reading`` document.
    """
    requests = set()
    for row in doc.items:
        if not row.meter_number:
            return None
        requests.update(
            frappe.get_all(
                CLAIM_DOCTYPE,
                filters={"customer": doc.customer, "serial_no": row.meter_number, "status": "Closed"},
                pluck=REQUEST_FIELD,
            )
        )

    if len(requests) != 1 or None in requests or "" in requests:
        return None

    return requests.pop()


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def customer_request_query(doctype, txt, searchfield, start, page_len, filters):
    """Search the customer's requests, limited to those of a property when one is given."""
    customer = filters.get("customer")
    if not customer:
        return []

    request = frappe.qb.DocType(USR_DOCTYPE)
    row = frappe.qb.DocType(USR_PROPERTY_DOCTYPE)
    query = (
        frappe.qb.from_(request)
        .select(request.name, request.customer_name)
        .where(request.customer == customer)
        .where(request.docstatus < 2)
        .where(request.name.like(f"%{txt}%"))
        .orderby(request.name, order=frappe.qb.desc)
        .limit(page_len)
        .offset(start)
    )

    utility_property = filters.get("utility_property")
    if utility_property:
        listed = frappe.qb.from_(row).select(row.parent).where(row.parenttype == USR_DOCTYPE).where(
            row.utility_property == utility_property
        )
        query = query.where((request.utility_property == utility_property) | request.name.isin(listed))

    return query.run()


@frappe.whitelist()
def warranty_claim_defaults(utility_service_request: str) -> dict | None:
    """Return what Create > Warranty Claim on a request needs, or ``None`` when it is not offered.

    Offered for a submitted request with a customer and a submitted Sales Order
    linked to it through ``Sales Order.utility_service_request``. The property
    is prefilled from the request's own, else from its one property row; with
    several property rows the user picks it.

    Args:
        utility_service_request: ``Utility Service Request`` name.

    Returns:
        ``{"claims": [...], "values": {...}}``: the request's Warranty Claims
        that are not Cancelled, and the new claim's values.
    """
    request = frappe.get_doc(USR_DOCTYPE, utility_service_request)
    request.check_permission("read")
    if (
        request.docstatus != 1
        or not request.customer
        or not frappe.db.exists("Sales Order", {REQUEST_FIELD: request.name, "docstatus": 1})
    ):
        return None

    properties = {row.utility_property for row in request.requested_properties if row.utility_property}
    return {
        "claims": frappe.get_all(
            CLAIM_DOCTYPE,
            filters={REQUEST_FIELD: request.name, "status": ("!=", "Cancelled")},
            pluck="name",
            order_by="creation",
        ),
        "values": {
            "customer": request.customer,
            "utility_property": request.get("utility_property")
            or (next(iter(properties)) if len(properties) == 1 else None),
            REQUEST_FIELD: request.name,
            "complaint_date": today(),
        },
    }


def meter_reading_offered(claim) -> bool:
    """Return whether Create > Meter Reading is offered on a Warranty Claim.

    For a saved, Closed claim with a customer and a serial number.
    """
    return bool(
        not claim.is_new()
        and frappe.db.get_value(CLAIM_DOCTYPE, claim.name, "status") == "Closed"
        and claim.customer
        and claim.serial_no
    )


@frappe.whitelist()
def make_meter_reading(source_name: str):
    """Return an unsaved Meter Reading for the meter of a Warranty Claim.

    Prefilled with the claim's customer, property, request and one row with its
    meter. The row's item is left for the user: the claim's item is the meter
    hardware, not the billed item. The price list is the customer's default,
    else its Customer Group's, as the Meter Reading form sets it.

    Args:
        source_name: ``Warranty Claim`` name.
    """
    claim = frappe.get_doc(CLAIM_DOCTYPE, source_name)
    claim.check_permission("read")
    if not meter_reading_offered(claim):
        frappe.throw(_("A Meter Reading needs a saved, Closed Warranty Claim with a customer and a serial number."))

    return build_meter_reading([claim])


@frappe.whitelist()
def make_meter_reading_from_claims(source_name):
    """Return one unsaved Meter Reading for the meters of several Warranty Claims.

    The claims must all be Closed, have a serial number and share one customer.
    One row per meter: two claims on one meter give one row. The request and
    property are set only when every claim has the same one.

    Args:
        source_name: ``Warranty Claim`` names, as a list or a JSON list.
    """
    names = list(dict.fromkeys(frappe.parse_json(source_name) if isinstance(source_name, str) else source_name))
    if not names:
        frappe.throw(_("Select at least one Warranty Claim."))

    claims = [frappe.get_doc(CLAIM_DOCTYPE, name) for name in names]
    for claim in claims:
        claim.check_permission("read")

    refused = [claim.name for claim in claims if not meter_reading_offered(claim)]
    if refused:
        frappe.throw(
            _("These Warranty Claims are not Closed or have no serial number: {0}.").format(", ".join(refused)),
            title=_("Cannot Create Meter Reading"),
        )

    customers = sorted({claim.customer for claim in claims})
    if len(customers) > 1:
        frappe.throw(
            _("The selected Warranty Claims belong to different customers ({0}). Select claims of one customer.").format(
                ", ".join(customers)
            ),
            title=_("Cannot Create Meter Reading"),
        )

    return build_meter_reading(claims)


def build_meter_reading(claims):
    """Return an unsaved Meter Reading for claims of one customer, one row per meter."""
    from utility_billing.utility_billing.doctype.meter_reading.meter_reading import get_customer_details

    customer = get_customer_details(claims[0].customer)
    reading = frappe.new_doc("Meter Reading")
    reading.update(
        {
            "customer": claims[0].customer,
            "customer_name": customer.customer_name,
            "territory": customer.territory,
            "price_list": customer.default_price_list,
            "property": shared_value(claims, "utility_property"),
            REQUEST_FIELD: shared_value(claims, REQUEST_FIELD),
        }
    )
    for serial in dict.fromkeys(claim.serial_no for claim in claims):
        reading.append("items", {"meter_number": serial})
    return reading


def shared_value(claims, fieldname: str):
    """Return the value every claim has for ``fieldname``, or ``None`` when they differ or any is blank."""
    values = {claim.get(fieldname) for claim in claims}
    return values.pop() if len(values) == 1 else None
