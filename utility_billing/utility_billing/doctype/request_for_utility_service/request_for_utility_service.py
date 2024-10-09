# Copyright (c) 2024, Navari and contributors
# For license information, please see license.txt

from frappe.contacts.address_and_contact import load_address_and_contact

# import frappe
from frappe.model.document import Document


class RequestforUtilityService(Document):
    def onload(self):
        load_address_and_contact(self)
