"""Utility Deferred Account child table.

Maps a company to the account that temporarily holds the revenue of deferred
Sales Invoice lines until the deferred posting date is reached.
"""

import frappe
from frappe import _
from frappe.model.document import Document


class UtilityDeferredAccount(Document):
	def validate(self) -> None:
		"""Validate that the deferred account belongs to the selected company."""
		account_company = frappe.db.get_value("Account", self.deferred_account, "company")

		if account_company and account_company != self.company:
			frappe.throw(
				_("Deferred Account {0} does not belong to company {1}.").format(
					frappe.bold(self.deferred_account), frappe.bold(self.company)
				)
			)
