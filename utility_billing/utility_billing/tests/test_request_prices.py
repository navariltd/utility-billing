"""Tests for finding a Utility Service Request's Item Prices by its lease window.

A request owns the Item Prices of its properties' service items that are scoped
to its customer and start inside the property's lease window. These tests run
real requests through submit, Define, the schedule editor, date edits and
cancel, and check which prices each step touches.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import flt, getdate

from utility_billing.utility_billing.tests import factories
from utility_billing.utility_billing.utils import item_price_actions, request_prices
from utility_billing.utility_billing.utils.item_price_summary_actions import save_item_price_schedule
from utility_billing.utility_billing.utils.item_rate import get_rate_for_date

PROPERTY = "_Test Window Property"
OTHER_PROPERTY = "_Test Window Other Property"
ITEM = "_Test Window Rent Item"
SECONDARY_ITEM = "_Test Window Electricity"
METER_ITEM = "_Test Window Water Meter"
PRICE_LIST = "_Test Window Price List"
CUSTOMER = "_Test Window Customer"
OTHER_CUSTOMER = "_Test Window Other Customer"


class RequestPricesTestCase(FrappeTestCase):
	"""Shared fixtures: one property, two customers and an Item Price site."""

	def setUp(self):
		super().setUp()
		self.company = frappe.db.get_value("Company", {}, "name")
		for item_code in (ITEM, SECONDARY_ITEM, METER_ITEM):
			factories.ensure_item(item_code)
			factories.delete_prices(item_code, PRICE_LIST)
		factories.ensure_price_list(PRICE_LIST)
		factories.ensure_property(PROPERTY, service_item=ITEM)
		factories.ensure_customer(CUSTOMER)
		factories.ensure_customer(OTHER_CUSTOMER)
		self._clear_requests()
		self._set_approach("Item Price")

	def tearDown(self):
		for item_code in (ITEM, SECONDARY_ITEM, METER_ITEM):
			factories.delete_prices(item_code, PRICE_LIST)
		self._clear_requests()
		super().tearDown()

	def _clear_requests(self):
		names = frappe.get_all(
			"Contract Utility Property Item",
			filters={"utility_property": ("in", [PROPERTY, OTHER_PROPERTY]), "parenttype": "Utility Service Request"},
			pluck="parent",
		)
		for name in set(names):
			frappe.db.delete("Contract Utility Property Item", {"parent": name})
			frappe.db.delete("Utility Service Request Item", {"parent": name})
			frappe.db.delete("Utility Service Request", {"name": name})

	def _set_approach(self, approach):
		saved = frappe.db.get_single_value("Utility Billing Settings", "rent_billing_approach")
		frappe.db.set_single_value("Utility Billing Settings", "rent_billing_approach", approach)
		frappe.clear_cache(doctype="Utility Billing Settings")
		self.addCleanup(self._restore_approach, saved)

	def _restore_approach(self, approach):
		frappe.db.set_single_value("Utility Billing Settings", "rent_billing_approach", approach)
		frappe.clear_cache(doctype="Utility Billing Settings")

	def _request(self, start, end, customer=CUSTOMER, submit=True, property_name=PROPERTY, items=None):
		"""Insert, and by default submit, a request leasing one property."""
		request = frappe.new_doc("Utility Service Request")
		request.update(
			{
				"company": self.company,
				"service_request_from": "Customer",
				"party_name": customer,
				"price_list": PRICE_LIST,
				# Only the row carries the end, so the header does not snap it to whole months.
				"start_date": start,
			}
		)
		request.append(
			"requested_properties",
			{
				"utility_property": property_name,
				"item_code": ITEM,
				"start_date": start,
				"end_date": end,
				"is_active": 1,
			},
		)
		for item_code in items or [ITEM]:
			request.append("items", {"item_code": item_code, "qty": 1, "rate": 100, "uom": "Nos"})
		request.flags.ignore_mandatory = True
		request.flags.ignore_links = True
		request.insert(ignore_permissions=True)
		if submit:
			request.submit()

		return request

	def _define(self, request, rate, replace=0, manual=None, property_name=PROPERTY):
		start, end = request_prices.lease_window(request, property_name)
		return item_price_actions.create_item_price_schedule(
			request.name,
			[property_name],
			{property_name: rate},
			str(start),
			str(end) if end else None,
			replace_existing=replace,
			manual_schedules={property_name: manual} if manual else None,
		)

	def _price(self, item_code, start, end, rate, customer=CUSTOMER, **values):
		doc = frappe.get_doc(
			{
				"doctype": "Item Price",
				"item_code": item_code,
				"price_list": PRICE_LIST,
				"uom": "Nos",
				"customer": customer,
				"price_list_rate": rate,
				"valid_from": start,
				"valid_upto": end,
				**values,
			}
		)
		doc.insert(ignore_permissions=True)

		return doc.name

	def _prices(self, item_code=ITEM):
		return [
			(str(row.valid_from), str(row.valid_upto) if row.valid_upto else None, flt(row.price_list_rate), row.customer)
			for row in frappe.get_all(
				"Item Price",
				filters={"item_code": item_code, "price_list": PRICE_LIST},
				fields=["valid_from", "valid_upto", "price_list_rate", "customer"],
				order_by="valid_from asc, customer asc",
			)
		]

	def _rate(self, request, date, customer=CUSTOMER):
		return get_rate_for_date(
			ITEM, date, customer=customer, price_list=PRICE_LIST, qty=1, service_request=request.name
		)

	def _bill(self, request, date, item_code=ITEM):
		"""Record a submitted Sales Invoice of the request billing ``item_code`` on ``date``."""
		invoice = frappe.get_doc(
			{
				"doctype": "Sales Invoice",
				"name": frappe.generate_hash(length=12),
				"customer": request.customer,
				"company": self.company,
				"posting_date": date,
				"utility_service_request": request.name,
				"docstatus": 1,
			}
		)
		invoice.db_insert()
		line = frappe.get_doc(
			{
				"doctype": "Sales Invoice Item",
				"name": frappe.generate_hash(length=12),
				"parent": invoice.name,
				"parenttype": "Sales Invoice",
				"parentfield": "items",
				"item_code": item_code,
				"qty": 1,
				"rate": 1,
				"custom_posting_date": date,
				"docstatus": 1,
			}
		)
		line.db_insert()
		self.addCleanup(frappe.db.delete, "Sales Invoice Item", {"parent": invoice.name})
		self.addCleanup(frappe.db.delete, "Sales Invoice", {"name": invoice.name})

		return invoice.name


class TestReplaceExisting(RequestPricesTestCase):
	"""Which rows Replace Existing deletes, for each case of the review."""

	def test_back_to_back_same_customer_deletes_only_the_later_lease(self):
		first = self._request("2030-01-01", "2030-03-31")
		second = self._request("2030-04-01", "2030-06-30")
		self._define(first, 10000)
		self._define(second, 12000)

		self._define(second, 13000, replace=1)

		self.assertEqual(
			self._prices(),
			[("2030-01-01", "2030-03-31", 10000, CUSTOMER), ("2030-04-01", "2030-06-30", 13000, CUSTOMER)],
		)

	def test_back_to_back_different_customer_deletes_only_the_later_lease(self):
		first = self._request("2030-01-01", "2030-03-31", customer=OTHER_CUSTOMER)
		second = self._request("2030-04-01", "2030-06-30")
		self._define(first, 10000)
		self._define(second, 12000)

		self._define(second, 13000, replace=1)

		self.assertEqual(
			self._prices(),
			[
				("2030-01-01", "2030-03-31", 10000, OTHER_CUSTOMER),
				("2030-04-01", "2030-06-30", 13000, CUSTOMER),
			],
		)

	def test_a_spilling_price_of_the_earlier_lease_is_kept(self):
		"""A legacy price running past its lease end starts in its own window, so it stays."""
		self._request("2030-01-01", "2030-03-31")
		second = self._request("2030-04-01", "2030-06-30")
		self._price(ITEM, "2030-01-01", "2030-05-31", 10000)

		self._define(second, 12000, replace=1)

		self.assertIn(("2030-01-01", "2030-05-31", 10000, CUSTOMER), self._prices())

	def test_a_spilling_price_of_another_customer_is_kept(self):
		self._request("2030-01-01", "2030-03-31", customer=OTHER_CUSTOMER)
		second = self._request("2030-04-01", "2030-06-30")
		self._price(ITEM, "2030-01-01", "2030-05-31", 10000, customer=OTHER_CUSTOMER)
		self._define(second, 12000)

		self._define(second, 13000, replace=1)

		self.assertEqual(
			self._prices(),
			[
				("2030-01-01", "2030-05-31", 10000, OTHER_CUSTOMER),
				("2030-04-01", "2030-06-30", 13000, CUSTOMER),
			],
		)

	def test_replace_after_the_start_moved_deletes_the_moved_price(self):
		"""The price followed the lease when its start moved, so Replace still finds it."""
		second = self._request("2030-04-01", "2030-06-30")
		self._define(second, 12000)

		second.reload()
		second.requested_properties[0].start_date = "2030-05-01"
		second.save(ignore_permissions=True)
		self.assertEqual(self._prices(), [("2030-05-01", "2030-06-30", 12000, CUSTOMER)])

		self._define(second, 13000, replace=1)

		self.assertEqual(self._prices(), [("2030-05-01", "2030-06-30", 13000, CUSTOMER)])

	def test_replace_never_deletes_blank_customer_or_secondary_prices(self):
		request = self._request("2030-01-01", "2030-06-30", items=[ITEM, SECONDARY_ITEM])
		self._define(request, 10000)
		self._price(ITEM, "2030-02-01", "2030-02-28", 999, customer=None)
		self._price(SECONDARY_ITEM, "2030-01-01", "2030-06-30", 25)
		self._price(METER_ITEM, "2030-01-01", "2030-06-30", 40, is_fixed_meter_charge=1)

		self._define(request, 11000, replace=1)

		self.assertIn(("2030-02-01", "2030-02-28", 999, None), self._prices())
		self.assertEqual(self._prices(SECONDARY_ITEM), [("2030-01-01", "2030-06-30", 25, CUSTOMER)])
		self.assertEqual(self._prices(METER_ITEM), [("2030-01-01", "2030-06-30", 40, CUSTOMER)])


class TestWindowGuards(RequestPricesTestCase):
	"""What may be written into a window."""

	def test_define_rejects_a_manual_period_past_the_lease_end(self):
		request = self._request("2030-01-01", "2030-06-30")
		manual = [{"valid_from": "2030-01-01", "valid_upto": "2030-09-30", "rate": 10000}]

		with self.assertRaises(frappe.ValidationError):
			self._define(request, 10000, manual=manual)

		self.assertEqual(self._prices(), [])

	def test_editor_rejects_add_period_past_the_lease_end(self):
		request = self._request("2030-01-01", "2030-06-30")
		self._define(request, 10000)

		with self.assertRaises(frappe.ValidationError):
			save_item_price_schedule(
				request.name,
				{
					PROPERTY: {
						"periods": [
							{"valid_from": "2030-01-01", "valid_upto": "2030-12-31", "price_list_rate": 10000}
						],
						"deleted": [],
					}
				},
			)

	def test_open_ended_period_is_cut_when_the_lease_gets_an_end(self):
		request = self._request("2030-01-01", None)
		save_item_price_schedule(
			request.name,
			{
				PROPERTY: {
					"periods": [{"valid_from": "2030-01-01", "valid_upto": "2099-12-31", "price_list_rate": 9000}],
					"deleted": [],
				}
			},
		)

		request.reload()
		# The form sets the length with the end; a stored length of 0 keeps a row open ended.
		request.requested_properties[0].end_date = "2030-06-30"
		request.requested_properties[0].contract_length_months = 5
		request.save(ignore_permissions=True)

		self.assertEqual(self._prices(), [("2030-01-01", "2030-06-30", 9000, CUSTOMER)])

	def test_define_needs_the_request_customer(self):
		request = self._request("2030-01-01", "2030-06-30")
		frappe.db.set_value("Utility Service Request", request.name, "customer", None)
		request.reload()

		with self.assertRaises(frappe.ValidationError):
			self._define(request, 10000)
		with self.assertRaises(frappe.ValidationError):
			save_item_price_schedule(
				request.name,
				{PROPERTY: {"periods": [{"valid_from": "2030-01-01", "valid_upto": "2030-06-30", "price_list_rate": 1}]}},
			)

		self.assertEqual(self._prices(), [])

	def test_define_for_another_customer_is_rejected(self):
		request = self._request("2030-01-01", "2030-06-30")

		with self.assertRaises(frappe.ValidationError):
			item_price_actions.create_item_price_schedule(
				request.name, [PROPERTY], {PROPERTY: 10000}, "2030-01-01", "2030-06-30", customer=OTHER_CUSTOMER
			)

		self.assertEqual(self._prices(), [])

	def test_define_needs_a_submitted_request(self):
		draft = self._request("2030-01-01", "2030-06-30", submit=False)

		with self.assertRaises(frappe.ValidationError):
			self._define(draft, 10000)

		self.assertEqual(self._prices(), [])

	def test_editor_still_works_on_a_draft_request(self):
		"""The summary offers the editor on drafts, so the server does not refuse it."""
		draft = self._request("2030-01-01", "2030-06-30", submit=False)

		result = save_item_price_schedule(
			draft.name,
			{PROPERTY: {"periods": [{"valid_from": "2030-01-01", "valid_upto": "2030-06-30", "price_list_rate": 8000}]}},
		)

		self.assertEqual(result["created"], 1)

	def test_a_future_dated_request_has_its_own_window(self):
		current = self._request("2030-01-01", "2030-06-30")
		future = self._request("2031-01-01", "2031-06-30")
		self._define(current, 10000)

		self._define(future, 15000, replace=1)
		self._define(future, 16000, replace=1)

		self.assertEqual(
			self._prices(),
			[("2030-01-01", "2030-06-30", 10000, CUSTOMER), ("2031-01-01", "2031-06-30", 16000, CUSTOMER)],
		)
		self.assertEqual(self._rate(current, "2030-03-10"), 10000)
		self.assertEqual(self._rate(future, "2031-03-10"), 16000)
		self.assertIsNone(self._rate(future, "2030-03-10"))


class TestWindowLookup(RequestPricesTestCase):
	"""The primary line rate of a request comes from its own window only."""

	def test_a_later_blank_customer_price_is_ignored(self):
		request = self._request("2030-01-01", "2030-06-30")
		self._define(request, 12000)
		self._price(ITEM, "2030-03-01", None, 999, customer=None)

		self.assertEqual(self._rate(request, "2030-04-10"), 12000)

	def test_a_neighbouring_lease_price_is_not_used(self):
		first = self._request("2030-01-01", "2030-03-31")
		second = self._request("2030-04-01", "2030-06-30")
		self._price(ITEM, "2030-01-01", "2030-05-31", 10000)

		self.assertIsNone(self._rate(second, "2030-04-10"))
		self.assertEqual(self._rate(first, "2030-02-10"), 10000)


class TestLeaseMove(RequestPricesTestCase):
	"""Editing lease dates after submit carries the prices with the lease."""

	def test_shortening_the_lease_cuts_and_deletes_prices(self):
		request = self._request("2030-01-01", "2030-12-31")
		self._define(
			request,
			0,
			manual=[
				{"valid_from": "2030-01-01", "valid_upto": "2030-06-30", "rate": 10000},
				{"valid_from": "2030-07-01", "valid_upto": "2030-12-31", "rate": 11000},
			],
		)

		request.reload()
		request.requested_properties[0].end_date = "2030-05-31"
		request.save(ignore_permissions=True)

		self.assertEqual(self._prices(), [("2030-01-01", "2030-05-31", 10000, CUSTOMER)])

	def test_a_later_lease_can_be_priced_after_the_earlier_one_shrinks(self):
		first = self._request("2030-01-01", "2030-12-31")
		self._define(first, 10000)

		first.reload()
		first.requested_properties[0].end_date = "2030-06-30"
		first.save(ignore_permissions=True)
		later = self._request("2030-07-01", "2030-12-31")
		result = self._define(later, 15000)

		self.assertEqual(result["created_count"], 1)
		self.assertEqual(self._rate(later, "2030-08-10"), 15000)

	def test_moving_the_lease_away_from_a_billed_date_is_blocked(self):
		request = self._request("2030-01-01", "2030-12-31")
		self._define(request, 10000)
		self._bill(request, "2030-07-10")

		request.reload()
		request.requested_properties[0].end_date = "2030-06-30"
		with self.assertRaises(frappe.ValidationError):
			request.save(ignore_permissions=True)

		self.assertEqual(self._prices(), [("2030-01-01", "2030-12-31", 10000, CUSTOMER)])

	def test_moving_the_lease_leaves_secondary_and_meter_prices_alone(self):
		request = self._request("2030-01-01", "2030-12-31", items=[ITEM, SECONDARY_ITEM])
		self._define(request, 10000)
		self._price(SECONDARY_ITEM, "2030-01-01", "2030-12-31", 25)
		self._price(METER_ITEM, "2030-01-01", "2030-12-31", 40, is_fixed_meter_charge=1)

		request.reload()
		request.requested_properties[0].end_date = "2030-03-31"
		request.save(ignore_permissions=True)

		self.assertEqual(self._prices(SECONDARY_ITEM), [("2030-01-01", "2030-12-31", 25, CUSTOMER)])
		self.assertEqual(self._prices(METER_ITEM), [("2030-01-01", "2030-12-31", 40, CUSTOMER)])

	def test_update_after_submit_with_a_blank_primary_cost_center_saves(self):
		request = self._request("2030-01-01", "2030-12-31")
		frappe.db.set_value("Utility Service Request Item", request.items[0].name, "cost_center", None)

		request.reload()
		request.remarks = "edited after submit"
		request.save(ignore_permissions=True)

		self.assertIsNone(frappe.db.get_value("Utility Service Request Item", request.items[0].name, "cost_center"))


class TestCancel(RequestPricesTestCase):
	"""Cancelling a request deletes its own window prices and nothing else."""

	def test_cancel_deletes_only_the_request_window(self):
		first = self._request("2030-01-01", "2030-03-31")
		second = self._request("2030-04-01", "2030-06-30", items=[ITEM, SECONDARY_ITEM])
		self._define(first, 10000)
		self._define(second, 12000)
		self._price(ITEM, "2030-05-01", "2030-05-31", 999, customer=None)
		self._price(ITEM, "2030-05-01", "2030-05-31", 777, customer=OTHER_CUSTOMER)
		self._price(SECONDARY_ITEM, "2030-04-01", "2030-06-30", 25)
		self._price(METER_ITEM, "2030-04-01", "2030-06-30", 40, is_fixed_meter_charge=1)

		second.reload()
		second.cancel()

		self.assertEqual(
			self._prices(),
			[
				("2030-01-01", "2030-03-31", 10000, CUSTOMER),
				("2030-05-01", "2030-05-31", 999, None),
				("2030-05-01", "2030-05-31", 777, OTHER_CUSTOMER),
			],
		)
		self.assertEqual(self._prices(SECONDARY_ITEM), [("2030-04-01", "2030-06-30", 25, CUSTOMER)])
		self.assertEqual(self._prices(METER_ITEM), [("2030-04-01", "2030-06-30", 40, CUSTOMER)])


class TestSharedRentItem(RequestPricesTestCase):
	"""A service item owned by two properties stops every price write and delete."""

	def setUp(self):
		super().setUp()
		self.request = self._request("2030-01-01", "2030-06-30")
		self._define(self.request, 10000)
		factories.ensure_property(OTHER_PROPERTY, service_item=ITEM)
		self.addCleanup(frappe.db.set_value, "Utility Property", OTHER_PROPERTY, "service_item", None)

	def _assert_blocked(self, action, *args, **kwargs):
		with self.assertRaises(frappe.ValidationError) as caught:
			action(*args, **kwargs)
		self.assertIn(PROPERTY, str(caught.exception))
		self.assertIn(OTHER_PROPERTY, str(caught.exception))
		self.assertEqual(self._prices(), [("2030-01-01", "2030-06-30", 10000, CUSTOMER)])

	def test_define_and_replace_stop(self):
		self._assert_blocked(self._define, self.request, 11000)
		self._assert_blocked(self._define, self.request, 11000, replace=1)

	def test_editor_stops(self):
		price = frappe.db.get_value("Item Price", {"item_code": ITEM, "price_list": PRICE_LIST}, "name")
		self._assert_blocked(
			save_item_price_schedule,
			self.request.name,
			{
				PROPERTY: {
					"periods": [
						{"name": price, "valid_from": "2030-01-01", "valid_upto": "2030-06-30", "price_list_rate": 5}
					]
				}
			},
		)
		self._assert_blocked(
			item_price_actions.update_item_price_rates, self.request.name, [{"name": price, "price_list_rate": 5}]
		)

	def test_cancel_stops(self):
		self.request.reload()
		# A failed web request rolls back; the savepoint does the same here.
		frappe.db.savepoint("shared_cancel")
		try:
			self._assert_blocked(self.request.cancel)
		finally:
			frappe.db.rollback(save_point="shared_cancel")

		self.assertEqual(frappe.db.get_value("Utility Service Request", self.request.name, "docstatus"), 1)


class TestAutoRepeatSite(RequestPricesTestCase):
	"""Under Auto Repeat no price path runs; a request edit behaves as on develop."""

	def setUp(self):
		super().setUp()
		self.request = self._request("2030-01-01", "2030-12-31", items=[ITEM, SECONDARY_ITEM])
		self._define(self.request, 10000)
		self._price(ITEM, "2030-03-01", None, 999, customer=None)
		self._set_approach("Auto Repeat")
		self.before = self._prices()

	def test_define_editor_and_rate_edits_refuse(self):
		with self.assertRaises(frappe.ValidationError):
			self._define(self.request, 11000, replace=1)
		with self.assertRaises(frappe.ValidationError):
			save_item_price_schedule(self.request.name, {PROPERTY: {"periods": []}})
		price = frappe.db.get_value("Item Price", {"item_code": ITEM, "customer": CUSTOMER}, "name")
		with self.assertRaises(frappe.ValidationError):
			item_price_actions.update_item_price_rates(self.request.name, [{"name": price, "price_list_rate": 5}])

		self.assertEqual(self._prices(), self.before)

	def test_date_edit_leaves_prices_and_ignores_billed_dates(self):
		self._bill(self.request, "2030-11-10")

		self.request.reload()
		self.request.requested_properties[0].end_date = "2030-06-30"
		self.request.save(ignore_permissions=True)

		self.assertEqual(self._prices(), self.before)

	def test_date_edit_with_a_shared_rent_item_is_not_blocked(self):
		factories.ensure_property(OTHER_PROPERTY, service_item=ITEM)
		self.addCleanup(frappe.db.set_value, "Utility Property", OTHER_PROPERTY, "service_item", None)

		self.request.reload()
		self.request.requested_properties[0].end_date = "2030-06-30"
		self.request.save(ignore_permissions=True)

		self.assertEqual(self._prices(), self.before)

	def test_cancel_deletes_nothing(self):
		self.request.reload()
		self.request.cancel()

		self.assertEqual(self._prices(), self.before)

	def test_rate_lookup_is_erpnext_s_own(self):
		"""The window is not applied, so ERPNext's latest valid_from wins, as on develop."""
		self.assertEqual(self._rate(self.request, "2030-04-10"), 999)
