"""Tests for defining the Item Prices of a request with several properties.

The Define dialog prices one property at a time, each with its own increments.
Pricing the second property never touches the first one's prices. One call
mixing properties with different starts is refused. The request summary lists
the properties already priced, so the dialog opens on the first one without
prices. Save Schedule accepts a schedule ending the day before a lease end of
whole months.

Every test runs in a savepoint rolled back afterwards.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import flt

from utility_billing.utility_billing.tests import lease_fixtures as fx
from utility_billing.utility_billing.utils import item_price_actions
from utility_billing.utility_billing.utils.item_price_summary_actions import save_item_price_schedule

A = "_Test Several Properties A"
B = "_Test Several Properties B"
START = "2026-01-01"
END = "2027-01-01"
A_INCREMENT = {"interval_months": 6, "percentage": 10, "effective_after_months": 0, "basis": "Original Amount"}
B_INCREMENT = {"interval_months": 12, "percentage": 5, "effective_after_months": 0, "basis": "Original Amount"}


def prices_of(item_code):
	return [
		(str(price.valid_from), str(price.valid_upto), flt(price.price_list_rate))
		for price in frappe.get_all(
			"Item Price",
			filters={"item_code": item_code, "price_list": fx.PRICE_LIST, "customer": fx.CUSTOMER},
			fields=["valid_from", "valid_upto", "price_list_rate"],
			order_by="valid_from asc",
		)
	]


class SeveralPropertiesCase(fx.SavepointMixin, FrappeTestCase):
	def setUp(self):
		super().setUp()
		fx.use_approach("Item Price")
		for name in (A, B):
			fx.lease_property(name)
			frappe.db.delete("Item Price", {"item_code": name, "price_list": fx.PRICE_LIST})

	def define(self, request, properties, rates, increment, start, replace=1, preview=False):
		"""Call the Define action as the dialog does."""
		args = {
			"docname": request.name,
			"properties": frappe.as_json(properties),
			"base_rates": frappe.as_json(rates),
			"start_date": start,
			"price_list": fx.PRICE_LIST,
			"customer": fx.CUSTOMER,
			"frequency": "Monthly",
			"increment": frappe.as_json(increment),
		}
		if preview:
			return item_price_actions.preview_item_price_schedule(**args)

		return item_price_actions.create_item_price_schedule(**args, replace_existing=replace)


class TestOnePropertyAtATime(SeveralPropertiesCase):
	"""The dialog flow: the first property, then the second."""

	def test_same_starts_each_property_keeps_its_own_increments(self):
		request = fx.make_request([(A, START, END), (B, START, END)], START, END)

		self.define(request, [A], {A: 10000}, A_INCREMENT, START)
		a_prices = prices_of(A)
		self.define(request, [B], {B: 15000}, B_INCREMENT, START)

		self.assertEqual(a_prices, [("2026-01-01", "2026-06-30", 10000), ("2026-07-01", "2026-12-31", 11000)])
		self.assertEqual(prices_of(B), [("2026-01-01", "2026-12-31", 15000)])
		self.assertEqual(prices_of(A), a_prices)

	def test_different_starts_each_property_stops_on_its_last_day(self):
		# B keeps the request's end, as the form fills it: the request's anniversary.
		request = fx.make_request([(A, START, END), (B, "2026-04-15", END)], START, END)

		self.define(request, [A], {A: 10000}, A_INCREMENT, START)
		a_prices = prices_of(A)
		self.define(request, [B], {B: 15000}, B_INCREMENT, "2026-04-15")

		self.assertEqual(prices_of(B), [("2026-04-15", "2026-12-31", 15000)])
		self.assertEqual(prices_of(A), a_prices)

	def test_a_property_added_to_a_submitted_request_is_priced_alone(self):
		request = fx.make_request([(A, START, END)], START, END)
		self.define(request, [A], {A: 10000}, A_INCREMENT, START)
		a_prices = prices_of(A)

		request.reload()
		request.append(
			"requested_properties",
			{
				"utility_property": B,
				"item_code": B,
				"start_date": "2026-06-12",
				"end_date": "2026-12-12",
				"is_active": 1,
				"rent_billing_approach": "Item Price",
			},
		)
		request.save(ignore_permissions=True)
		self.define(request, [B], {B: 15000}, {**B_INCREMENT, "interval_months": 3}, "2026-06-12")

		self.assertEqual(
			prices_of(B), [("2026-06-12", "2026-09-11", 15000), ("2026-09-12", "2026-12-11", 15750)]
		)
		self.assertEqual(prices_of(A), a_prices)

	def test_replace_on_and_off_leave_the_other_property_alone(self):
		request = fx.make_request([(A, START, END), (B, START, END)], START, END)
		self.define(request, [A], {A: 10000}, A_INCREMENT, START)
		a_prices = prices_of(A)

		self.define(request, [B], {B: 15000}, B_INCREMENT, START, replace=0)
		self.define(request, [B], {B: 16000}, B_INCREMENT, START, replace=1)

		self.assertEqual(prices_of(B), [("2026-01-01", "2026-12-31", 16000)])
		self.assertEqual(prices_of(A), a_prices)


class TestOneCallForSeveral(SeveralPropertiesCase):
	"""One call naming several properties."""

	def test_different_starts_are_refused_before_anything_is_written(self):
		request = fx.make_request([(A, START, END), (B, "2026-04-15", END)], START, END)
		self.define(request, [A], {A: 10000}, A_INCREMENT, START)
		a_prices = prices_of(A)

		for preview in (True, False):
			with self.subTest(preview=preview), self.assertRaisesRegex(frappe.ValidationError, "start on different dates"):
				self.define(request, [A, B], {A: 10000, B: 15000}, A_INCREMENT, "2026-04-15", preview=preview)

		self.assertEqual(prices_of(A), a_prices)

	def test_same_starts_are_accepted(self):
		request = fx.make_request([(A, START, END), (B, START, END)], START, END)

		result = self.define(request, [A, B], {A: 10000, B: 15000}, A_INCREMENT, START)

		self.assertEqual(result["created_count"], 4)
		self.assertEqual(prices_of(B), [("2026-01-01", "2026-06-30", 15000), ("2026-07-01", "2026-12-31", 16500)])


class TestPricedProperties(SeveralPropertiesCase):
	def test_the_summary_lists_the_properties_already_priced(self):
		request = fx.make_request([(A, START, END), (B, START, END)], START, END)
		summary = lambda: item_price_actions.get_item_price_summary(request.name)

		self.assertEqual(summary()["priced_properties"], [])
		self.assertFalse(summary()["has_prices"])

		self.define(request, [A], {A: 10000}, A_INCREMENT, START)
		self.assertEqual(summary()["priced_properties"], [A])

		self.define(request, [B], {B: 15000}, B_INCREMENT, START)
		self.assertEqual(sorted(summary()["priced_properties"]), sorted([A, B]))
		self.assertTrue(summary()["has_prices"])


class TestSaveScheduleEnd(SeveralPropertiesCase):
	"""Save Schedule and the day after the last billed day."""

	def test_the_one_day_period_of_an_old_schedule_can_be_removed(self):
		request = fx.make_request([(A, START, END)], START, END)
		self.define(request, [A], {A: 10000}, A_INCREMENT, START)
		old = frappe.get_doc(
			{
				"doctype": "Item Price",
				"item_code": A,
				"price_list": fx.PRICE_LIST,
				"customer": fx.CUSTOMER,
				"uom": "Nos",
				"price_list_rate": 12000,
				"valid_from": END,
				"valid_upto": END,
			}
		).insert(ignore_permissions=True)
		kept = frappe.get_all(
			"Item Price",
			filters={"item_code": A, "price_list": fx.PRICE_LIST, "name": ("!=", old.name)},
			fields=["name", "valid_from", "valid_upto", "price_list_rate", "customer"],
			order_by="valid_from asc",
		)

		result = save_item_price_schedule(
			request.name,
			frappe.as_json(
				{
					A: {
						"periods": [
							{
								"name": price.name,
								"valid_from": str(price.valid_from),
								"valid_upto": str(price.valid_upto),
								"price_list_rate": price.price_list_rate,
								"customer": price.customer,
							}
							for price in kept
						],
						"deleted": [old.name],
					}
				}
			),
		)

		self.assertEqual(result["deleted"], 1)
		self.assertEqual(prices_of(A)[-1], ("2026-07-01", "2026-12-31", 11000))

	def test_a_schedule_stopping_earlier_is_still_refused(self):
		request = fx.make_request([(A, START, END)], START, END)

		with self.assertRaises(frappe.ValidationError):
			save_item_price_schedule(
				request.name,
				frappe.as_json(
					{
						A: {
							"periods": [
								{
									"valid_from": START,
									"valid_upto": "2026-12-30",
									"price_list_rate": 1000,
									"customer": fx.CUSTOMER,
								}
							],
							"deleted": [],
						}
					}
				),
			)
