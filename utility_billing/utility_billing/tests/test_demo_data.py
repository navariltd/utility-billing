"""Consistency checks for the JSON dataset used by demo generation.

These tests do not create records. They catch broken links and malformed tariff
blocks in the demo data before a site is populated.
"""

import json
from pathlib import Path

import frappe
from frappe.tests import UnitTestCase

DATA_DIR = Path(__file__).resolve().parents[1] / "patches/demo/data"


def load(name: str) -> list[dict]:
	"""Return one demo JSON file as a list of records."""
	return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


class TestDemoData(UnitTestCase):
	"""The demo JSON files must describe one coherent dataset."""

	def test_properties_have_parents_media_and_valid_child_doctype(self):
		properties = load("utility_property.json")
		groups = {row["property_name"] for row in properties if row.get("is_group")}
		units = [row for row in properties if not row.get("is_group")]

		self.assertTrue(groups)
		self.assertTrue(units)

		for unit in units:
			self.assertIn(unit["parent_utility_property"], groups)
			self.assertTrue(unit["cover_image"].startswith("https://"))
			self.assertTrue(unit["image_gallery"])

		for row in properties:
			self.assertTrue(row["cover_image"].startswith("https://"))
			self.assertTrue(row["image_gallery"])
			for feature in row.get("features", []):
				self.assertEqual(feature["doctype"], "Utility Property Feature item")

	def test_rents_requests_and_rules_reference_known_records(self):
		properties = {
			row["property_name"] for row in load("utility_property.json") if not row.get("is_group")
		}
		customers = {row["customer_name"] for row in load("customer.json")}
		rules = {row["rule_name"] for row in load("billing_adjustment_rule.json")}
		rents = {row["property_name"]: row["monthly_rent"] for row in load("property_rent.json")}

		self.assertEqual(set(rents), properties)
		self.assertTrue(all(rate > 0 for rate in rents.values()))

		assigned = set()
		for request in load("utility_service_request.json"):
			self.assertIn(request["party_name"], customers)
			for row in request["requested_properties"]:
				self.assertIn(row["utility_property"], properties)
				self.assertIn(row["adjustment_rule"], rules)
				self.assertNotIn(row["utility_property"], assigned)
				assigned.add(row["utility_property"])

	def test_portal_users_reference_customers(self):
		customers = {row["customer_name"] for row in load("customer.json")}
		users = load("portal_user.json")

		self.assertEqual({row["customer"] for row in users}, customers)
		self.assertEqual(len({row["email"] for row in users}), len(users))
		for row in users:
			self.assertIn("demo.utilitybilling.test", row["email"])

	def test_meter_readings_reference_known_customers_and_properties(self):
		customers = {row["customer_name"] for row in load("customer.json")}
		properties = {row["property_name"] for row in load("utility_property.json")}

		for reading in load("meter_reading.json"):
			self.assertIn(reading["customer"], customers)
			self.assertIn(reading["property"], properties)
			self.assertTrue(reading["items"])
			for item in reading["items"]:
				self.assertIn(item["item_code"], {"Water", "Electricity"})
				self.assertGreater(item["consumption"], 0)

	def test_meter_prices_have_contiguous_tariff_blocks(self):
		prices = [
			row for row in load("item_price.json") if row["item_code"] in {"Water", "Electricity", "Sewer"}
		]
		price_lists = {row["price_list"] for row in prices}

		self.assertEqual(price_lists, {"Standard Residential", "Standard Commercial"})

		for price in prices:
			tariffs = price["tariffs"]
			self.assertTrue(tariffs)
			self.assertEqual(tariffs[0]["lower_limit"], 0)
			for previous, current in zip(tariffs, tariffs[1:], strict=False):
				self.assertEqual(current["lower_limit"], previous["upper_limit"])
			self.assertGreater(tariffs[-1]["upper_limit"], tariffs[-2]["upper_limit"])

	def test_support_tickets_reference_known_records(self):
		customers = {row["customer_name"] for row in load("customer.json")}
		properties = {row["property_name"] for row in load("utility_property.json")}
		statuses = {"Open", "Replied", "On Hold", "Resolved", "Closed"}

		for issue in load("support_issue.json"):
			self.assertIn(issue["customer"], customers)
			self.assertIn(issue["property"], properties)
			self.assertIn(issue["status"], statuses)

	def test_uom_masters_are_loaded_before_items(self):
		doctypes = frappe.get_hooks("utility_demo_master_doctypes")

		self.assertLess(doctypes.index("uom"), doctypes.index("item"))

		unit = load("uom.json")[0]
		self.assertEqual(unit["uom_name"], "Unit")
		self.assertEqual(unit["enabled"], 1)
