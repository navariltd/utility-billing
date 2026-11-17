# Copyright (c) 2025, Navari and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate
from frappe.model.document import Document

class UtilityBillStructure(Document):
	def validate(self):
		self.validate_billing()
		self.calculate_total()

	def calculate_total(self):
		total = 0.0
		for item in self.items:
			amount = 0 if item.get("calculation_type") == "Formula" or item.get("condition") else float(item.amount or 0)
			discount = float(item.discount or 0)

			item.total = amount - ((discount / 100) * amount)
			total += item.total if item.get("row_type") != "Calculation Only" else 0

		self.total_amount = total

	def validate_billing(self):
		if self.start_date and self.end_date and getdate(self.end_date) < getdate(self.start_date):
			frappe.throw(_('End Date must be on or after Start Date.'))
		for row in self.items:
			if flt(row.amount) < 0 or not 0 <= flt(row.discount) <= 100:
				frappe.throw(_('Monthly charges must be nonnegative and discounts between 0 and 100.'))
		from ...utils.billing_formula import validate_formulas
		validate_formulas(self)
		if self.get('metered_billing') and not self.water_item:
			frappe.throw(_('Metered billing requires a Consumption Item.'))
		if self.water_item and self.water_item == self.sewerage_item:
			frappe.throw(_('Water and sewerage must use different items.'))
		groups = {}
		for band in self.bands:
			key = band.get('item') or ''
			if not key and not (flt(band.get('water_rate')) or flt(band.get('sewerage_rate'))):
				frappe.throw(_('Select an Item for each consumption band.'))
			minimum, maximum = flt(band.get('min_qty')), flt(band.upper_limit)
			if minimum < 0 or maximum <= minimum:
				frappe.throw(_('Band Min Qty must be nonnegative and Max Qty must be greater than Min Qty.'))
			if any(flt(band.get(k)) < 0 for k in ('rate', 'water_rate', 'sewerage_rate')):
				frappe.throw(_('Band rates cannot be negative.'))
			groups.setdefault(key, []).append((minimum, maximum))
		for ranges in groups.values():
			previous_max = None
			for minimum, maximum in sorted(ranges):
				if previous_max is not None and minimum < previous_max:
					frappe.throw(_('Consumption bands for the same item cannot overlap.'))
				previous_max = maximum
