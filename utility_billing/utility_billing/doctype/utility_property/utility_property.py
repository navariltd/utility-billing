# Copyright (c) 2024, Navari and contributors
# For license information, please see license.txt

# import frappe
from frappe.utils.nestedset import NestedSet
from frappe.contacts.address_and_contact import load_address_and_contact


class UtilityProperty(NestedSet):
    def onload(self):
     load_address_and_contact(self)
