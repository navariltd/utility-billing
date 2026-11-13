from frappe.model.document import Document

from ...utils.request_link import check_request_customer


def validate(doc: Document, method: str) -> None:
	check_request_customer(doc)
