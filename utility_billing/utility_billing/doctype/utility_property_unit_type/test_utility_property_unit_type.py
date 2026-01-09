# Copyright (c) 2025, Navari and Contributors
# See license.txt

# import frappe
from frappe.tests.utils import FrappeTestCase

# On IntegrationTestCase, the doctype test records and all
# link-field test record dependencies are recursively loaded
# Use these module variables to add/remove to/from that list
EXTRA_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]
IGNORE_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]


class UnitTestUtilityPropertyUnitType(FrappeTestCase):
	"""
	Unit tests for UtilityPropertyUnitType.
	Use this class for testing individual functions and methods.
	"""

	pass


class IntegrationTestUtilityPropertyUnitType(FrappeTestCase):
	"""
	Integration tests for UtilityPropertyUnitType.
	Use this class for testing interactions between multiple components.
	"""

	pass
