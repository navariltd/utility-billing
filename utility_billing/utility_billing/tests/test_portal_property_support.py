"""Property-page support tests: tenancy access and ticket creation."""

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase, UnitTestCase

from utility_billing.api.portal.support import (
	create_property_support_issue,
	get_property_support,
)
from utility_billing.api.portal.support_context import (
	find_current_tenancy,
	get_property_context,
)

PROPERTY = "PROP-SUPPORT-TEST"
CONTRACT = "CON-SUPPORT-TEST"
CUSTOMER = "C-SUPPORT-TEST"


class TestPropertySupportContext(UnitTestCase):
	"""Only current tenancies can open a property support workspace."""

	def test_property_without_current_tenancy_is_rejected(self):
		with (
			patch(
				"utility_billing.api.portal.support_context.find_current_tenancy",
				return_value=None,
			),
			patch(
				"frappe.db.get_value",
				return_value=frappe._dict(property_name="Kanha B2", company="Test Co"),
			),
		):
			with self.assertRaises(frappe.PermissionError):
				get_property_context(PROPERTY)

	def test_active_contract_wins_over_a_reservation(self):
		properties = {
			"current": [
				frappe._dict(utility_property=PROPERTY, contract="CON-RESERVED", state="Reserved"),
				frappe._dict(utility_property=PROPERTY, contract="CON-ACTIVE", state="Active"),
			],
			"history": [],
		}

		with patch(
			"utility_billing.api.portal.support_context.get_tenant_properties",
			return_value=properties,
		):
			tenancy = find_current_tenancy(PROPERTY)

		self.assertEqual(tenancy["contract"], "CON-ACTIVE")

	def test_context_uses_contract_customer_and_service_request(self):
		tenancy = frappe._dict(
			utility_property=PROPERTY,
			contract=CONTRACT,
			state="Active",
		)
		values = {
			("Utility Property", PROPERTY): frappe._dict(
				property_name="Kanha B2",
				company="Test Co",
			),
			("Contract", CONTRACT): frappe._dict(
				party_name=CUSTOMER,
				utility_service_request="USR-ORIGIN",
			),
			("Customer", CUSTOMER): "Jane Doe",
		}

		def fake_get_value(doctype, name, *args, **kwargs):
			return values[(doctype, name)]

		with (
			patch(
				"utility_billing.api.portal.support_context.find_current_tenancy",
				return_value=tenancy,
			),
			patch(
				"utility_billing.api.portal.support_context.get_portal_customers",
				return_value=[{"name": CUSTOMER, "customer_name": "Jane Doe"}],
			),
			patch("frappe.db.get_value", side_effect=fake_get_value),
		):
			context = get_property_context(PROPERTY)

		self.assertEqual(context["property"], PROPERTY)
		self.assertEqual(context["reference"], CONTRACT)
		self.assertEqual(context["customer"], CUSTOMER)
		self.assertEqual(context["customer_name"], "Jane Doe")
		self.assertEqual(context["service_request"], "USR-ORIGIN")
		self.assertEqual(context["company"], "Test Co")


class TestPropertySupportEndpoint(IntegrationTestCase):
	"""A property ticket links the unit and stays visible on the property page."""

	def test_property_ticket_is_created_without_a_booking(self):
		company = frappe.db.get_value("Company", {}, "name")
		customer_doc = frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": f"Property Support {frappe.generate_hash(length=6)}",
				"customer_type": "Individual",
			}
		).insert(ignore_permissions=True)
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": f"support-property-{frappe.generate_hash(length=8)}@example.com",
				"first_name": "Support",
				"last_name": "Tester",
				"send_welcome_email": 0,
			}
		).insert(ignore_permissions=True)
		context = {
			"name": PROPERTY,
			"reference": CONTRACT,
			"customer": customer_doc.name,
			"customer_name": customer_doc.customer_name,
			"property": PROPERTY,
			"property_name": "Property Support Test",
			"company": company,
			"service_request": None,
		}

		frappe.set_user(user.name)
		try:
			with (
				patch(
					"utility_billing.api.portal.support.get_property_context",
					return_value=context,
				),
				patch("frappe.model.document.Document._validate_links", lambda self: None),
			):
				created = create_property_support_issue(
					PROPERTY,
					"Broken window latch",
					"The bedroom window does not close and the unit is exposed.",
				)
				workspace = get_property_support(PROPERTY)
		finally:
			frappe.set_user("Administrator")

		self.assertEqual(created["issue"]["property"], PROPERTY)
		self.assertIsNone(created["issue"]["service_request"])
		self.assertEqual(created["issue"]["customer"], customer_doc.name)
		self.assertEqual(created["issue"]["status"], "Open")
		self.assertEqual(workspace["context"]["customer"], customer_doc.name)
		self.assertEqual(workspace["counts"]["open"], 1)
		self.assertIn(
			created["issue"]["name"],
			[issue["name"] for issue in workspace["issues"]],
		)
