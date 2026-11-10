"""Tests for the lock on a request's Contract terms (``request_contract_lock``).

Under Item Price a request with a Contract that is not cancelled cannot have its
dates, contract length or property rows changed, from any path: the form, REST,
Data Import or the portal. Its other fields still save. Under Auto Repeat
nothing is locked, as on develop.

Every test runs in a savepoint rolled back afterwards; code that commits runs
with commits disabled.
"""

import os
import tempfile
from unittest.mock import patch

import frappe
from frappe.core.doctype.data_import.importer import UPDATE, Importer
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, add_months, getdate, today

from utility_billing.api.portal import booking_actions
from utility_billing.utility_billing.doctype.utility_service_request.utility_service_request import (
	create_contract,
)
from utility_billing.utility_billing.tests import lease_fixtures as fx

P1 = "_Test Request Lock P1"
P2 = "_Test Request Lock P2"
P3 = "_Test Request Lock P3"
START = getdate(add_months(today(), 1)).replace(day=1)
END = getdate(add_months(START, 12))
SUBMITTED = "This request has Contract"
DRAFT = "This request has draft Contract"


def named(message: str, contract: str) -> str:
	"""Return a pattern for a lock message naming the Contract, which is shown in bold."""
	return f"{message} <strong>{contract}</strong>"


def import_end_date(service_request: str, end_date) -> None:
	"""Update a request's end date through Data Import, as a user's CSV would."""
	path = os.path.join(tempfile.mkdtemp(), "request_lock.csv")
	with open(path, "w") as handle:
		handle.write(f"ID,Contract End Date\n{service_request},{end_date}\n")

	data_import = frappe.get_doc(
		{"doctype": "Data Import", "reference_doctype": "Utility Service Request", "import_type": UPDATE}
	)
	importer = Importer("Utility Service Request", data_import=data_import, file_path=path, console=True)
	# Data Import Log is a MyISAM table, outside the test's savepoint, and the
	# console log is written to a file in the sites folder
	with (
		fx.no_commit(),
		patch.object(frappe.db, "rollback"),
		patch(f"{Importer.__module__}.create_import_log"),
		patch.object(importer, "print_import_log"),
	):
		importer.import_data()


class RequestLockCase(fx.SavepointMixin, FrappeTestCase):
	approach = "Item Price"

	def setUp(self):
		super().setUp()
		fx.use_approach(self.approach)
		for name in (P1, P2, P3):
			fx.lease_property(name)

	def request(self, *properties, submit=True):
		return fx.make_request([(name, START, END) for name in properties or (P1,)], START, END, submit=submit)

	def move_end(self, request, months=-1):
		"""Move the request's end date and its rows' end dates."""
		request.reload()
		request.end_date = add_months(END, months)
		request.contract_length_months = None
		for row in request.requested_properties:
			row.end_date = request.end_date
		request.save(ignore_permissions=True)


class TestSubmittedContract(RequestLockCase):
	"""A submitted request with a submitted Contract."""

	def setUp(self):
		super().setUp()
		self.usr = self.request(P1, P2)
		self.contract = fx.make_contract(self.usr.name)

	def assert_locked(self, change):
		self.usr.reload()
		change(self.usr)
		with self.assertRaisesRegex(frappe.ValidationError, named(SUBMITTED, self.contract.name)):
			self.usr.save(ignore_permissions=True)

	def test_moving_the_dates_is_refused(self):
		with self.assertRaisesRegex(frappe.ValidationError, "Cancel the Contract, or create a new request"):
			self.move_end(self.usr)

	def test_moving_a_row_start_is_refused(self):
		self.assert_locked(lambda usr: setattr(usr.requested_properties[0], "start_date", add_days(START, 10)))

	def test_changing_the_contract_length_is_refused(self):
		def change(usr):
			usr.contract_length_months = 13
			usr.end_date = None

		self.assert_locked(change)

	def test_releasing_a_row_is_refused(self):
		self.assert_locked(lambda usr: setattr(usr.requested_properties[0], "is_active", 0))

	def test_adding_a_row_is_refused(self):
		self.assert_locked(
			lambda usr: usr.append(
				"requested_properties",
				{"utility_property": P3, "item_code": P3, "start_date": START, "end_date": END, "is_active": 1},
			)
		)

	def test_removing_a_row_is_refused(self):
		self.assert_locked(lambda usr: usr.requested_properties.pop())

	def test_other_fields_still_save(self):
		self.usr.reload()
		self.usr.remarks = "Gate code 1234"
		self.usr.items[0].rate = 1500
		self.usr.save(ignore_permissions=True)

		self.usr.reload()
		self.assertEqual((self.usr.remarks, self.usr.items[0].rate), ("Gate code 1234", 1500))

	def test_rows_removed_and_added_again_unchanged_still_save(self):
		self.usr.reload()
		rows = [row.as_dict() for row in self.usr.requested_properties]
		self.usr.set("requested_properties", [])
		for row in rows:
			row.pop("name")
			self.usr.append("requested_properties", row)
		self.usr.save(ignore_permissions=True)

	def test_the_contract_is_left_unchanged(self):
		modified = frappe.db.get_value("Contract", self.contract.name, "modified")
		with self.assertRaises(frappe.ValidationError):
			self.move_end(self.usr)

		self.assertEqual(frappe.db.get_value("Contract", self.contract.name, "modified"), modified)

	def test_rest_save_is_refused(self):
		self.usr.reload()
		doc = self.usr.as_dict()
		doc["remarks"] = "via REST"
		doc["requested_properties"][0]["start_date"] = str(add_days(START, 10))

		with self.assertRaisesRegex(frappe.ValidationError, SUBMITTED):
			frappe.client.save(doc)

	def test_rest_set_value_is_refused(self):
		with self.assertRaisesRegex(frappe.ValidationError, SUBMITTED):
			frappe.client.set_value("Utility Service Request", self.usr.name, "end_date", str(add_months(END, 1)))

	def test_data_import_is_refused(self):
		control = self.request(P3)

		later = getdate(add_months(END, 1))

		import_end_date(self.usr.name, later)
		import_end_date(control.name, later)

		self.assertEqual(frappe.db.get_value("Utility Service Request", self.usr.name, "end_date"), END)
		self.assertEqual(frappe.db.get_value("Utility Service Request", control.name, "end_date"), later)

	def test_the_portal_still_refuses_with_its_own_message(self):
		with (
			patch.object(booking_actions, "get_own_request", return_value=frappe.get_doc("Utility Service Request", self.usr.name)),
			self.assertRaisesRegex(frappe.ValidationError, "already has a Contract"),
		):
			booking_actions.modify_booking(self.usr.name, notes="New notes")


class TestDraftContract(RequestLockCase):
	def test_a_draft_contract_refuses_the_change(self):
		usr = self.request(P1)
		draft = fx.make_contract(usr.name, submit=False)

		with self.assertRaisesRegex(frappe.ValidationError, named(DRAFT, draft.name) + ". Delete it or submit it first"):
			self.move_end(usr)

	def test_deleting_the_draft_unlocks_the_request(self):
		usr = self.request(P1)
		draft = fx.make_contract(usr.name, submit=False)
		frappe.delete_doc("Contract", draft.name, ignore_permissions=True)

		self.move_end(usr)

		self.assertEqual(frappe.db.get_value("Utility Service Request", usr.name, "end_date"), getdate(add_months(END, -1)))

	def test_a_draft_request_with_a_contract_is_locked_too(self):
		usr = self.request(P1, submit=False)
		draft = frappe.get_doc("Contract", create_contract(usr.name))

		usr.reload()
		usr.requested_properties[0].start_date = add_days(START, 10)
		with self.assertRaisesRegex(frappe.ValidationError, named(DRAFT, draft.name)):
			usr.save(ignore_permissions=True)

	def test_a_draft_request_with_a_contract_can_still_be_submitted(self):
		usr = self.request(P1, submit=False)
		create_contract(usr.name)

		usr.reload()
		usr.submit()

		self.assertEqual(usr.docstatus, 1)


class TestCancelledOrNoContract(RequestLockCase):
	def test_a_cancelled_contract_counts_as_none(self):
		usr = self.request(P1)
		contract = fx.make_contract(usr.name)
		contract.cancel()

		self.move_end(usr)

		self.assertEqual(frappe.db.get_value("Utility Service Request", usr.name, "end_date"), getdate(add_months(END, -1)))

	def test_no_contract_stays_editable(self):
		usr = self.request(P1, P2)

		self.move_end(usr)
		usr.reload()
		usr.requested_properties[1].is_active = 0
		usr.save(ignore_permissions=True)

		self.assertEqual(frappe.db.get_value("Utility Service Request", usr.name, "end_date"), getdate(add_months(END, -1)))

	def test_the_portal_still_saves_a_booking_without_contract(self):
		usr = self.request(P1, submit=False)

		with patch.object(booking_actions, "get_own_request", return_value=frappe.get_doc("Utility Service Request", usr.name)):
			booking_actions.modify_booking(usr.name, end_date=str(add_months(END, -1)))

		self.assertEqual(frappe.db.get_value("Utility Service Request", usr.name, "end_date"), getdate(add_months(END, -1)))


class TestAutoRepeatUnchanged(RequestLockCase):
	"""Under Auto Repeat nothing is locked, as on develop: the Contract keeps its old dates."""

	approach = "Auto Repeat"

	def test_a_request_with_a_submitted_contract_stays_editable(self):
		usr = self.request(P1, P2)
		contract = fx.make_contract(usr.name)

		self.move_end(usr)
		usr.reload()
		usr.requested_properties[1].is_active = 0
		usr.save(ignore_permissions=True)

		self.assertEqual(frappe.db.get_value("Utility Service Request", usr.name, "end_date"), getdate(add_months(END, -1)))
		self.assertEqual(frappe.db.get_value("Contract", contract.name, "end_date"), END)

	def test_a_request_with_a_draft_contract_stays_editable(self):
		usr = self.request(P1)
		draft = fx.make_contract(usr.name, submit=False)

		self.move_end(usr)

		self.assertEqual(frappe.db.get_value("Contract", draft.name, "end_date"), END)
