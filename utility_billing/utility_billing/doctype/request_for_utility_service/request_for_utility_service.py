# Copyright (c) 2024, Navari and contributors
# For license information, please see license.txt

import frappe
from frappe.contacts.address_and_contact import load_address_and_contact
from frappe.model.document import Document


class RequestforUtilityService(Document):
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
                    "nrcpassport_no": self.nrcpassport_no,
                    "organisation_registration_no": self.organisation_registration_no,
                }
            )
            customer.insert()