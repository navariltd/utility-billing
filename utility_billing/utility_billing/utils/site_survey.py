"""The site survey Issue of a Utility Service Request.

Create > Site Survey opens an Issue for the request. For a Lead it carries the
Lead, since Issue links to Lead only (not to a Prospect or a CRM Deal), and it
carries the request's property: its own, else its one property row's. Once the
party is converted to a customer, the request's survey Issues without a
customer get it.
"""

import frappe


def survey_lead(doc) -> str | None:
    """Return the Lead of a request made for a Lead, else ``None``."""
    return doc.party_name if doc.get("service_request_from") == "Lead" else None


def survey_property(doc) -> str | None:
    """Return the request's property, else the one property its rows name, else ``None``.

    With rows for several different properties nothing is guessed.
    """
    if doc.get("utility_property"):
        return doc.utility_property

    properties = {row.utility_property for row in doc.get("requested_properties") or [] if row.utility_property}
    return properties.pop() if len(properties) == 1 else None


def fill_survey_customer(service_request: str, customer: str | None) -> list[str]:
    """Give the request's survey Issues that have no customer the request's customer.

    A direct update: the Issue is not saved, so its status, modified date and
    notifications are left alone. A customer already set is never changed.

    Args:
        service_request: ``Utility Service Request`` name.
        customer: The customer the request now has.

    Returns:
        The Issues updated.
    """
    if not customer:
        return []

    issues = frappe.get_all(
        "Issue",
        filters={"utility_service_request": service_request, "customer": ("is", "not set")},
        pluck="name",
    )
    customer_name = frappe.db.get_value("Customer", customer, "customer_name")
    for issue in issues:
        frappe.db.set_value(
            "Issue", issue, {"customer": customer, "customer_name": customer_name}, update_modified=False
        )

    return issues
