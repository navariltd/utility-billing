"""Unit tests for property service item item-group selection."""

from unittest.mock import patch

import frappe
from frappe.tests import UnitTestCase

from utility_billing.utility_billing.utils.service_item import (
	_is_usable_item_group,
	_resolve_fallback_item_group,
)

MODULE = "utility_billing.utility_billing.utils.service_item"


class TestServiceItemGroup(UnitTestCase):
	"""Service items must only use leaf Utility Item Groups."""

	def test_missing_group_is_not_usable(self):
		self.assertFalse(_is_usable_item_group(None))

	@patch(f"{MODULE}.frappe.db.get_value")
	def test_leaf_utility_group_is_usable(self, get_value):
		get_value.return_value = frappe._dict(is_group=0, is_utility_item_group=1)

		self.assertTrue(_is_usable_item_group("Utilities"))

	@patch(f"{MODULE}.frappe.db.get_value")
	def test_parent_group_is_not_usable(self, get_value):
		get_value.return_value = frappe._dict(is_group=1, is_utility_item_group=1)

		self.assertFalse(_is_usable_item_group("All Item Groups"))

	@patch(f"{MODULE}.frappe.db.get_value")
	def test_non_utility_group_is_not_usable(self, get_value):
		get_value.return_value = frappe._dict(is_group=0, is_utility_item_group=0)

		self.assertFalse(_is_usable_item_group("Fixed Asset"))

	@patch(f"{MODULE}._is_usable_item_group", return_value=False)
	@patch(f"{MODULE}.frappe.get_all", return_value=["Utilities"])
	def test_fallback_uses_a_leaf_utility_group(self, get_all, _is_usable):
		self.assertEqual(_resolve_fallback_item_group(), "Utilities")
		get_all.assert_called_once()
