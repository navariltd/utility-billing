"""Unit tests for the portal meter reading listing.

The tests feed unsaved rows to the pure helpers, so they never touch the
database.
"""

import frappe
from frappe.tests import UnitTestCase

from utility_billing.api.portal.meter_readings import (
	_attach_amounts,
	_attach_items,
	_attach_property_labels,
	_label_rates,
	_payload,
	_property_label,
)


def _reading(name: str = "MR-0001", property_name: str = "UP-1") -> frappe._dict:
	return frappe._dict(
		name=name,
		date="2026-10-01",
		customer="CUST-1",
		customer_name="Tenant",
		property=property_name,
		company="Company",
		currency="KES",
		docstatus=1,
	)


def _item(parent: str, previous: float, current: float, consumption: float = 0) -> frappe._dict:
	return frappe._dict(
		parent=parent,
		item_code="WATER",
		item_name="Water",
		meter_number="MTR-1",
		uom="Unit",
		previous_reading=previous,
		current_reading=current,
		consumption=consumption,
	)


class TestMeterReadingItems(UnitTestCase):
	"""Meter lines are grouped per reading and their consumption totalled."""

	def test_items_are_grouped_by_reading(self):
		readings = [_reading("MR-1"), _reading("MR-2")]
		_attach_items(
			readings,
			[_item("MR-1", 10, 15), _item("MR-2", 5, 8), _item("MR-2", 100, 130)],
		)

		self.assertEqual([len(reading["items"]) for reading in readings], [1, 2])
		self.assertEqual(readings[1]["total_consumption"], 33)

	def test_consumption_falls_back_to_reading_difference(self):
		readings = [_reading("MR-1")]
		_attach_items(readings, [_item("MR-1", 100, 160, consumption=0)])

		self.assertEqual(readings[0]["items"][0]["consumption"], 60)
		self.assertEqual(readings[0]["total_consumption"], 60)

	def test_stored_consumption_is_kept(self):
		readings = [_reading("MR-1")]
		_attach_items(readings, [_item("MR-1", 100, 160, consumption=55)])

		self.assertEqual(readings[0]["total_consumption"], 55)

	def test_reading_without_items_has_zero_consumption(self):
		readings = [_reading("MR-1")]
		_attach_items(readings, [])

		self.assertEqual(readings[0]["items"], [])
		self.assertEqual(readings[0]["total_consumption"], 0)


class TestBlockDistribution(UnitTestCase):
	"""Tariff block rows are totalled per reading and labelled with their meter."""

	def test_amounts_are_summed_per_reading(self):
		readings = [_reading("MR-1"), _reading("MR-2")]
		_attach_amounts(
			readings,
			[
				frappe._dict(parent="MR-1", amount=500),
				frappe._dict(parent="MR-1", amount=125),
				frappe._dict(parent="MR-2", amount=75),
			],
		)

		self.assertEqual(readings[0]["total_amount"], 625)
		self.assertEqual(readings[1]["total_amount"], 75)

	def test_reading_without_blocks_has_zero_amount(self):
		readings = [_reading("MR-1")]
		_attach_amounts(readings, [])

		self.assertEqual(readings[0]["total_amount"], 0)

	def test_blocks_are_labelled_with_their_meter_line(self):
		items = [
			frappe._dict(
				name="ITEM-1",
				item_code="WATER",
				item_name="Water",
				meter_number="MTR-1",
				uom="Unit",
			)
		]
		rates = [
			frappe._dict(meter_reading_item="ITEM-1", item_code="WATER", block="Block 1"),
			frappe._dict(meter_reading_item=None, item_code="METER", block=None),
		]

		_label_rates(rates, items)

		self.assertEqual(rates[0]["item_name"], "Water")
		self.assertEqual(rates[0]["meter_number"], "MTR-1")
		self.assertIsNone(rates[1]["meter_number"])
		self.assertEqual(rates[1]["item_name"], "METER")


class TestPropertyLabel(UnitTestCase):
	"""Units are labelled with the most specific identifier available."""

	def test_unit_number_wins(self):
		row = frappe._dict(
			name="UP-1", unit_number="A-12", house_no="7", plot_no="3", property_name="Block A"
		)

		self.assertEqual(_property_label(row), "A-12")

	def test_falls_back_through_plot_number_to_property_name(self):
		row = frappe._dict(name="UP-1", unit_number=None, house_no=None, plot_no="3")

		self.assertEqual(_property_label(row), "3")
		self.assertEqual(_property_label(frappe._dict(name="UP-1")), "UP-1")
		self.assertIsNone(_property_label(None))

	def test_label_attached_to_readings(self):
		readings = [_reading("MR-1", "UP-1"), _reading("MR-2", "UP-MISSING")]
		_attach_property_labels(readings, {"UP-1": frappe._dict(name="UP-1", house_no="7")})

		self.assertEqual(readings[0]["property_label"], "7")
		self.assertIsNone(readings[1]["property_label"])


class TestPayload(UnitTestCase):
	"""Totals summarise the returned page of readings."""

	def test_empty_payload(self):
		payload = _payload(None, [], [], [])

		self.assertEqual(payload["meter_readings"], [])
		self.assertEqual(
			payload["totals"],
			{
				"readings": 0,
				"consumption": 0,
				"amount": 0,
				"currency": None,
				"latest_date": None,
			},
		)

	def test_totals_use_first_row_as_latest(self):
		readings = [_reading("MR-1"), _reading("MR-2")]
		_attach_items(readings, [_item("MR-1", 0, 5), _item("MR-2", 0, 12)])
		_attach_amounts(
			readings,
			[
				frappe._dict(parent="MR-1", amount=250),
				frappe._dict(parent="MR-2", amount=600),
			],
		)

		payload = _payload("CUST-1", [{"name": "CUST-1"}], readings, [])

		self.assertEqual(payload["customer"], "CUST-1")
		self.assertEqual(payload["totals"]["readings"], 2)
		self.assertEqual(payload["totals"]["consumption"], 17)
		self.assertEqual(payload["totals"]["amount"], 850)
		self.assertEqual(payload["totals"]["currency"], "KES")
		self.assertEqual(payload["totals"]["latest_date"], "2026-10-01")

