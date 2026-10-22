"""Tests for the portal role, capability and tenancy helper functions.

These tests are pure unit tests: the helpers under test only depend on the
values passed in, so no documents are created and no database is touched.
"""

from frappe.tests import UnitTestCase

from utility_billing.api.portal.properties import ACTIVE, HISTORY, RESERVED, classify_lease_item
from utility_billing.api.portal.roles import (
	GUEST,
	LANDLORD_ROLE,
	MANAGER_ROLE,
	PORTAL_CAPABILITIES,
	TENANT_ROLE,
	UTILITY_CUSTOMER_ROLE,
	get_portal_capabilities,
	resolve_portal_role,
)


class TestPortalRoleResolution(UnitTestCase):
	"""Portal role resolution from Frappe roles plus tenancy linkage."""

	def test_no_roles_resolves_to_guest(self):
		self.assertEqual(resolve_portal_role([], has_linked_customer=False), GUEST)

	def test_customer_with_linked_customer_resolves_to_tenant(self):
		self.assertEqual(
			resolve_portal_role(["Customer", "Website User"], has_linked_customer=True),
			TENANT_ROLE,
		)

	def test_customer_without_linked_customer_has_no_portal_role(self):
		self.assertEqual(resolve_portal_role(["Customer"], has_linked_customer=False), "")

	def test_explicit_tenant_role_requires_linked_customer(self):
		self.assertEqual(resolve_portal_role([TENANT_ROLE], has_linked_customer=False), "")
		self.assertEqual(resolve_portal_role([TENANT_ROLE], has_linked_customer=True), TENANT_ROLE)

	def test_property_manager_takes_precedence_over_tenant(self):
		self.assertEqual(
			resolve_portal_role([MANAGER_ROLE, "Customer"], has_linked_customer=True),
			MANAGER_ROLE,
		)

	def test_landlord_alias_resolves_to_property_owner(self):
		self.assertEqual(resolve_portal_role(["Landlord"], has_linked_customer=False), LANDLORD_ROLE)

	def test_utility_customer_role(self):
		self.assertEqual(
			resolve_portal_role([UTILITY_CUSTOMER_ROLE], has_linked_customer=False),
			UTILITY_CUSTOMER_ROLE,
		)

	def test_unknown_roles_have_no_portal_role(self):
		self.assertEqual(resolve_portal_role(["System Manager", "Website User"]), "")


class TestPortalCapabilities(UnitTestCase):
	"""Capability map granted to each portal role."""

	def test_guest_can_only_browse_properties(self):
		capabilities = get_portal_capabilities(GUEST)

		self.assertTrue(capabilities["browse_properties"])
		for capability in PORTAL_CAPABILITIES:
			if capability != "browse_properties":
				self.assertFalse(capabilities[capability], capability)

	def test_authenticated_portal_roles_receive_every_capability(self):
		for portal_role in (TENANT_ROLE, LANDLORD_ROLE, MANAGER_ROLE, UTILITY_CUSTOMER_ROLE):
			capabilities = get_portal_capabilities(portal_role)
			self.assertEqual(set(capabilities), set(PORTAL_CAPABILITIES))
			self.assertTrue(all(capabilities.values()), portal_role)


class TestLeaseItemClassification(UnitTestCase):
	"""Classification of contract property allocations for the tenant portal."""

	def test_signed_live_allocation_is_active(self):
		self.assertEqual(
			classify_lease_item(is_active=1, end_date="2030-01-31", contract_is_signed=1),
			ACTIVE,
		)

	def test_unsigned_allocation_is_reserved(self):
		self.assertEqual(
			classify_lease_item(is_active=1, end_date="2030-01-31", contract_is_signed=0),
			RESERVED,
		)

	def test_inactive_allocation_is_history(self):
		self.assertEqual(
			classify_lease_item(is_active=0, end_date="2030-01-31", contract_is_signed=1),
			HISTORY,
		)

	def test_expired_allocation_is_history(self):
		self.assertEqual(
			classify_lease_item(
				is_active=1,
				end_date="2024-01-31",
				contract_is_signed=1,
				reference_date="2024-02-01",
			),
			HISTORY,
		)

	def test_allocation_ending_today_is_not_history(self):
		self.assertEqual(
			classify_lease_item(
				is_active=1,
				end_date="2024-02-01",
				contract_is_signed=1,
				reference_date="2024-02-01",
			),
			ACTIVE,
		)

	def test_open_ended_allocation_without_end_date_is_active(self):
		self.assertEqual(classify_lease_item(is_active=1, end_date=None, contract_is_signed=1), ACTIVE)
