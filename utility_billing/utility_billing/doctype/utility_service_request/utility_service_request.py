# Copyright (c) 2024, Navari and contributors
# For license information, please see license.txt

import frappe
from frappe.contacts.address_and_contact import load_address_and_contact
from frappe.model.document import Document


class UtilityServiceRequest(Document):
    def onload(self):
        load_address_and_contact(self)

    def on_submit(self):
        if not frappe.db.exists("Customer", self.customer_name):
            customer = frappe.get_doc(
                {
                    "doctype": "Customer",
                    "customer_name": self.customer_name,
                    "customer_type": self.customer_type,
                    "customer_group": self.customer_group,
                    "territory": self.territory,
                    "tax_id": self.tax_id,
                    "nrc_or_passport_no": self.nrcpassport_no,
                    "company": self.company,
                }
            )
            customer.insert()
