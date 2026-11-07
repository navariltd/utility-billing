"""Comparison tests: the lease readers stay as they were where Released On does not apply.

Run against the branch before the change and after it; every test must pass on
both. Under Auto Repeat a released row reads as before, whatever its Released
On, and under Item Price a row still held reads as before.
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, add_months, getdate, today

from utility_billing.api.portal.booking_payload import serialise_request
from utility_billing.api.portal.properties import ACTIVE, HISTORY, classify_lease_item
from utility_billing.utility_billing.report.tenancy_summary import tenancy_summary
from utility_billing.utility_billing.tests import lease_fixtures as fx
from utility_billing.utility_billing.utils import availability, lease_status
from utility_billing.utility_billing.utils.property_status import release_ended_leases

P1 = "_Test Release Compare P1"
START = getdate(add_months(today(), -2)).replace(day=1)
END = getdate(add_months(START, 12))
LATER = getdate(add_days(today(), 10))


class ComparisonCase(fx.SavepointMixin, FrappeTestCase):
	approach = "Item Price"

	def setUp(self):
		super().setUp()
		fx.use_approach(self.approach)
		fx.lease_property(P1)
		self.u1 = fx.make_request([(P1, START, END)], START, END)
		self.contract = fx.make_contract(self.u1.name)

	def readers(self):
		"""Return what every lease reader says about P1 today."""
		self.contract.reload()
		contract = lease_status.get_contracts_by_request([self.u1.name])[self.u1.name]
		rows = lease_status.get_contract_rows([contract.name])[contract.name]
		payload = serialise_request(frappe.get_doc("Utility Service Request", self.u1.name), contract=contract, contract_rows=rows)
		row = self.contract.properties[0]
		columns, data, *_rest = tenancy_summary.execute({"property": P1})
		report_row = [entry for entry in data if entry["property"] == P1][0]

		return {
			"held": P1 in availability.get_held_properties(None, [P1]),
			"allocation": payload["properties"][0],
			"lease_status": lease_status.derive_lease_status(1, contract, rows),
			"tenant": classify_lease_item(row.is_active, row.end_date, 1),
			"report_columns": [column["fieldname"] for column in columns],
			"report_row": {key: value for key, value in report_row.items() if key != "contract_length"},
			"active_filter": len([entry for entry in tenancy_summary.execute({"property": P1, "property_status": "Active"})[1] if entry["property"] == P1]),
		}


class TestAutoRepeatReleasedRow(ComparisonCase):
	"""Under Auto Repeat a released row holds nothing in the Contract readers, and its request row still holds."""

	approach = "Auto Repeat"

	def test_every_reader_reads_as_before(self):
		fx.release_rows(self.contract, 0, released_on=LATER)

		readers = self.readers()

		self.assertTrue(readers["held"])
		self.assertEqual(readers["allocation"]["allocation_status"], "Active")
		self.assertNotIn("released_on", readers["allocation"])
		self.assertEqual(readers["lease_status"], lease_status.EXPIRED)
		self.assertEqual(readers["tenant"], HISTORY)
		self.assertNotIn("released_on", readers["report_columns"])
		self.assertNotIn("released_on", readers["report_row"])
		self.assertEqual(readers["report_row"]["remaining_days"], (END - getdate(today())).days)
		self.assertEqual(readers["active_filter"], 0)

	def test_the_backstop_reads_the_request_row_as_before(self):
		fx.release_rows(self.contract, 0, released_on=LATER)
		frappe.db.set_value("Utility Property", P1, "status", "Occupied")

		with patch("utility_billing.utility_billing.utils.property_status.set_released_contracts_inactive"):
			release_ended_leases()

		self.assertEqual(fx.property_status(P1), "Occupied")


class TestItemPriceRowStillHeld(ComparisonCase):
	"""Under Item Price a row not released reads as before."""

	def test_every_reader_reads_as_before(self):
		readers = self.readers()

		self.assertTrue(readers["held"])
		self.assertEqual(readers["allocation"]["allocation_status"], "Active")
		self.assertNotIn("released_on", readers["allocation"])
		self.assertEqual(readers["lease_status"], lease_status.ACTIVE)
		self.assertEqual(readers["tenant"], ACTIVE)
		self.assertEqual(readers["report_row"]["remaining_days"], (END - getdate(today())).days)
		self.assertEqual(readers["active_filter"], 1)

	def test_the_backstop_keeps_a_running_lease(self):
		frappe.db.set_value("Utility Property", P1, "status", "Occupied")

		with patch("utility_billing.utility_billing.utils.property_status.set_released_contracts_inactive"):
			release_ended_leases()

		self.assertEqual(fx.property_status(P1), "Occupied")
