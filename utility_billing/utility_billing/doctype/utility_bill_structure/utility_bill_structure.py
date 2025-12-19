# Copyright (c) 2025, Navari and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class UtilityBillStructure(Document):
	def validate(self):
		self.calculate_total()

	def calculate_total(self):
		total = 0.0
		for item in self.items:
			amount = float(item.amount or 0)
			discount = float(item.discount or 0)

			item.total = amount - ((discount / 100) * amount)
			total += item.total

		self.total_amount = total
