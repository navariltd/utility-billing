"""Create the rent billing service item of existing utility properties.

Backfills ``Utility Property.service_item`` for properties created before the
service item feature existed. Idempotent: properties that already own a valid
service item are skipped.
"""

import frappe

from utility_billing.utility_billing.utils.service_item import ensure_service_item

BATCH_SIZE = 200


def execute() -> None:
    """Create service items for every billable property."""
    settings = frappe.get_cached_doc("Utility Billing Settings")
    if not settings.auto_create_service_item:
        return

    properties = frappe.get_all(
        "Utility Property",
        filters={"is_group": 0},
        pluck="name",
        limit_page_length=0,
    )

    for property_name in properties:
        try:
            ensure_service_item(property_name)
        except Exception:
            frappe.log_error(
                frappe.get_traceback(),
                f"Service item backfill failed for property {property_name}",
            )

    frappe.db.commit()
