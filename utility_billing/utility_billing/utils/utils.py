from frappe.model.document import Document
import frappe

def sync_meter_readings(
    doc: Document,
    items_field: str = "items",
    target_field: str = "meter_readings",
) -> None:
    """
    Sync Sales Order / Invoice meter_readings table from all Meter Reading items
    referenced in the Sales Order / Invoice items table, using meter_number as key.
    """

    items = getattr(doc, items_field, []) or []
    if not items:
        return

    unique_meter_readings = list({item.meter_reading for item in items if getattr(item, "meter_reading", None)})
    if not unique_meter_readings:
        return

    items_by_meter = {}
    for mr_name in unique_meter_readings:
        try:
            mr_doc = frappe.get_doc("Meter Reading", mr_name)
        except frappe.DoesNotExistError:
            frappe.throw(f"Meter Reading {mr_name} does not exist")

        for item in getattr(mr_doc, "items", []) or []:
            meter_number = getattr(item, "meter_number", None)
            if not meter_number:
                continue  

            items_by_meter[meter_number] = {
                "meter_reading": mr_name,
                "item_code": item.item_code,
                "item_name": getattr(item, "item_name", None),
                "stock_uom": getattr(item, "stock_uom", None),
                "meter_number": meter_number,
                "uom": getattr(item, "uom", None),
                "qty": getattr(item, "qty", 1),
                "current_reading": getattr(item, "current_reading", None),
                "previous_reading": getattr(item, "previous_reading", None),
                "consumption": getattr(item, "consumption", None),
                "description": getattr(item, "description", None),
            }

    existing_rows = getattr(doc, target_field, []) or []
    rows_by_meter = {
        row.meter_number: row
        for row in existing_rows
        if getattr(row, "meter_number", None)
    }

    for meter_number, data in items_by_meter.items():
        row = rows_by_meter.get(meter_number)
        if not row:
            row = doc.append(target_field, {})
            row.meter_number = meter_number

        for field, value in data.items():
            setattr(row, field, value)

    doc.set(
        target_field,
        [row for row in doc.get(target_field) if getattr(row, "meter_number", None) in items_by_meter]
    )



@frappe.whitelist()
def get_active_leases_for_customer(customer):
    """
    Return active leases (Contracts) for a customer
    where the linked property is active and matches utility_property.
    """

    if not customer:
        return []

    contracts = frappe.get_all(
        "Contract",
        filters={
            "party_type": "Customer",
            "party_name": customer,
            "status": "Active",
        },
        fields=["name"],
    )


    if not contracts:
        return []

    contract_names = [c.name for c in contracts]

    property_filters = {
        "parent": ["in", contract_names],
        "is_active": 1,
    }

    properties = frappe.get_all(
        "Contract Utility Property Item",   
        filters=property_filters,
        fields=["parent", "utility_property"],
    )

    active_contracts = list({p.utility_property for p in properties})

    return active_contracts

@frappe.whitelist()
def get_serial_numbers_from_warranty_claims(customer, utility_property=None):
	"""
	Fetch serial numbers from closed Warranty Claims for the given customer
	where utility_property matches the given one OR is not set.
	"""

	filters = {
		"customer": customer,
		"status": "Closed",
	}

	or_filters = [
		{"utility_property": ["is", "not set"]}
	]

	if utility_property:
		or_filters.insert(0, {
			"utility_property": utility_property
		})

	claims = frappe.get_all(
		"Warranty Claim",
		filters=filters,
		or_filters=or_filters,
		fields=["serial_no"],
	)

	serial_set = set()

	for claim in claims:
		if claim.get("serial_no"):
			for serial in claim["serial_no"].split("\n"):
				serial = serial.strip()
				if serial:
					serial_set.add(serial)

	return sorted(serial_set)