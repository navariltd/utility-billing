"""Price list resolution for a Utility Service Request.

A request needs a price list so item rates and the rent schedule can resolve.

A request for a Customer defaults to, in order: the price list chosen on it,
the customer's ``default_price_list``, then its Customer Group's. A request for
a Lead, Prospect or CRM Deal gets no default: the user picks one. Every request
needs a price list to be submitted, and one for a Lead, Prospect or CRM Deal
also to be sent for approval.

At submit the customer receives the request's price list when it would
otherwise have none: a customer the request converts, or an existing customer
without a default whose Customer Group has none either. A customer's default is
never overwritten.

Rate lookups use ``resolve_price_list`` without the group: the customer's
``default_price_list``, then the ``Default Price List`` in Utility Billing
Settings.
"""

import frappe
from frappe import _


def resolve_price_list(customer: str | None = None, use_customer_group: bool = False) -> str | None:
    """Return the price list to default a service request to.

    Args:
        customer: Customer the request belongs to, if any.
        use_customer_group: For a request's own default: after the customer's
            default, use its Customer Group's, and never the Settings default.
            Off for rate lookups, which resolve as before.

    Returns:
        The resolved price list, or ``None`` when none is configured.
    """
    if customer:
        customer_price_list, customer_group = frappe.db.get_value(
            "Customer", customer, ["default_price_list", "customer_group"]
        ) or (None, None)
        if customer_price_list:
            return customer_price_list

        if use_customer_group and customer_group:
            return frappe.db.get_value("Customer Group", customer_group, "default_price_list") or None

    if use_customer_group:
        return None

    return (
        frappe.db.get_single_value("Utility Billing Settings", "default_price_list")
        or None
    )


def apply_default_price_list(doc) -> None:
    """Set the price list on a service request for a Customer when it has none.

    An explicitly chosen price list is never overwritten, and a request for a
    Lead, Prospect or CRM Deal is left for the user to fill in.

    Args:
        doc: ``Utility Service Request`` document.
    """
    if doc.get("price_list") or doc.get("service_request_from") != "Customer":
        return

    price_list = resolve_price_list(doc.get("customer") or doc.get("party_name"), use_customer_group=True)
    if price_list:
        doc.price_list = price_list


@frappe.whitelist()
def get_default_price_list(customer: str | None = None) -> str | None:
    """Return the price list a new service request of ``customer`` defaults to."""
    if not (customer and frappe.db.exists("Customer", customer)):
        return None

    frappe.has_permission("Customer", "read", doc=customer, throw=True)
    return resolve_price_list(customer, use_customer_group=True)


def require_price_list(doc) -> None:
    """Refuse to submit a request without a price list.

    A request for a Lead, Prospect or CRM Deal is also refused on the first
    approval step of a workflow, the step that leaves the workflow's starting
    state, since nothing can default its price list.

    Args:
        doc: ``Utility Service Request`` document.
    """
    if doc.get("price_list"):
        return

    if doc.get("_action") == "submit":
        frappe.throw(_("Set a Price List before submitting this request."), title=_("Price List Required"))

    if doc.get("service_request_from") not in (None, "", "Customer") and is_first_approval_step(doc):
        frappe.throw(
            _("Set a Price List before sending this request for approval: a {0} has none to default to.").format(
                _(doc.service_request_from)
            ),
            title=_("Price List Required"),
        )


def is_first_approval_step(doc) -> bool:
    """Return whether a workflow is moving a draft out of its starting state.

    The step is any transition into a state the starting state leads to, so a
    request returned for amendment and sent again counts too.
    """
    from frappe.model.workflow import get_workflow_name

    workflow_name = get_workflow_name(doc.doctype)
    before = doc.get_doc_before_save()
    if not workflow_name or doc.docstatus != 0 or not before:
        return False

    workflow = frappe.get_cached_doc("Workflow", workflow_name)
    field = workflow.workflow_state_field
    if not workflow.states or before.get(field) == doc.get(field):
        return False

    start = workflow.states[0].state
    return doc.get(field) in {row.next_state for row in workflow.transitions if row.state == start}


def set_price_list_of_new_customer(customer, doc) -> None:
    """Give a customer just created from a request the request's price list.

    Only for a customer this conversion created and that has no default price
    list; an existing customer is never changed here.

    Args:
        customer: ``Customer`` document created by the conversion.
        doc: ``Utility Service Request`` document it was created from.
    """
    if customer and doc.get("price_list") and not customer.default_price_list:
        set_customer_price_list(customer, doc.price_list)


def fill_customer_price_list(doc) -> None:
    """At submit, give the request's customer its price list when it would have none.

    Only when the customer has no default price list and its Customer Group has
    none either, so a default is never overwritten and a group's still applies.

    Args:
        doc: Submitted ``Utility Service Request`` document.
    """
    customer = doc.get("customer") or frappe.db.get_value(doc.doctype, doc.name, "customer")
    if not (customer and doc.get("price_list")):
        return

    default_price_list, customer_group = frappe.db.get_value(
        "Customer", customer, ["default_price_list", "customer_group"]
    ) or (None, None)
    if default_price_list or (
        customer_group and frappe.db.get_value("Customer Group", customer_group, "default_price_list")
    ):
        return

    set_customer_price_list(frappe.get_doc("Customer", customer), doc.price_list)


def set_customer_price_list(customer, price_list: str) -> None:
    """Set a customer's default price list and record the change in its history.

    Written without the user's Customer permissions and without validating the
    customer: it follows from submitting or converting the request, which the
    user is allowed to do. The Version is recorded under the user's name.

    Args:
        customer: ``Customer`` document.
        price_list: Price list to set.
    """
    customer.db_set("default_price_list", price_list)
    customer.save_version()


def sales_order_price_list(customer: str | None) -> str:
    """Return the price list of a Sales Order created from a service request.

    The customer's default price list, else its Customer Group's, else the
    Selling Settings default (Standard Selling). The request's own price list
    is not used, and the customer is never changed.

    Args:
        customer: Customer of the order.
    """
    return (
        resolve_price_list(customer, use_customer_group=True)
        or frappe.db.get_single_value("Selling Settings", "selling_price_list")
        or "Standard Selling"
    )
