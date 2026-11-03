"""Tests for a request's Contracts following it, under Item Price.

When a submitted request's dates or property rows change, the change is saved
only with consent to update its Contracts (the ``__update_contract`` key the
form sends after asking), and then every Contract that is not cancelled
follows. Without consent the change is refused, which covers the API and
imports. The request's own checks run first and leave the Contract untouched.
Under Auto Repeat nothing changes from develop.

Every test runs in a savepoint rolled back afterwards.
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_months, getdate, today

from utility_billing.utility_billing.tests import lease_fixtures as fx
from utility_billing.utility_billing.utils.contract_sync import CONSENT_KEY, get_contracts_to_update

A = "_Test Contract Sync A"
B = "_Test Contract Sync B"
X = "_Test Contract Sync X"
START = getdate(add_months(today(), -2)).replace(day=1)
END = getdate(add_months(START, 12))
SHORTER_END = getdate(add_months(START, 9))
REQUEST_MODULE = "utility_billing.utility_billing.doctype.utility_service_request.utility_service_request"


def contract_view(name):
	contract = frappe.get_doc("Contract", name)
	return (
		contract.status,
		getdate(contract.start_date),
		getdate(contract.end_date),
		[
			(row.utility_property, getdate(row.start_date), getdate(row.end_date), row.is_active)
			for row in contract.properties
		],
	)


class ContractSyncCase(fx.SavepointMixin, FrappeTestCase):
	approach = "Item Price"

	def setUp(self):
		super().setUp()
		fx.use_approach(self.approach)
		for name in (A, B, X):
			fx.lease_property(name)
		self.request = fx.make_request([(A, START, END)], START, END)
		self.contract = fx.make_contract(self.request.name)
		self.draft = fx.make_contract(self.request.name, submit=False)
		self.draft.contract_terms = None
		self.draft.db_set("contract_terms", None)

	def edit(self, change, consent):
		request = frappe.get_doc("Utility Service Request", self.request.name)
		change(request)
		if consent:
			request.set(CONSENT_KEY, 1)
		request.save(ignore_permissions=True)
		return request

	@staticmethod
	def shorten(request):
		request.end_date = SHORTER_END
		request.contract_length_months = 9
		request.requested_properties[0].end_date = SHORTER_END

	@staticmethod
	def add_b(request):
		request.append(
			"requested_properties",
			{
				"utility_property": B,
				"item_code": B,
				"start_date": START,
				"end_date": SHORTER_END,
				"is_active": 1,
				"rent_billing_approach": "Item Price",
			},
		)


class TestRefusal(ContractSyncCase):
	"""Without consent the change is refused and nothing moves."""

	def test_moving_the_dates_is_refused(self):
		before = contract_view(self.contract.name)

		with self.assertRaisesRegex(frappe.ValidationError, "confirm updating the Contract"):
			self.edit(self.shorten, consent=False)

		self.assertEqual(contract_view(self.contract.name), before)

	def test_adding_a_property_is_refused(self):
		with self.assertRaisesRegex(frappe.ValidationError, "confirm updating the Contract"):
			self.edit(self.add_b, consent=False)

	def test_an_api_save_of_the_document_dict_needs_the_key(self):
		data = frappe.get_doc("Utility Service Request", self.request.name).as_dict()
		data["end_date"] = SHORTER_END
		data["requested_properties"][0]["end_date"] = SHORTER_END

		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(data).save(ignore_permissions=True)

		data[CONSENT_KEY] = 1
		frappe.get_doc(data).save(ignore_permissions=True)
		self.assertEqual(contract_view(self.contract.name)[2], SHORTER_END)

	def test_a_change_the_contract_does_not_copy_needs_no_consent(self):
		request = frappe.get_doc("Utility Service Request", self.request.name)
		request.remarks = "Unrelated"
		request.save(ignore_permissions=True)

	def test_the_form_is_told_which_contracts_would_change(self):
		request = frappe.get_doc("Utility Service Request", self.request.name)
		self.assertEqual(get_contracts_to_update(request.as_dict()), [])

		self.shorten(request)
		self.assertEqual(
			sorted(get_contracts_to_update(request.as_dict())), sorted([self.contract.name, self.draft.name])
		)


class TestSync(ContractSyncCase):
	"""With consent every Contract that is not cancelled follows."""

	def test_moved_dates_reach_the_submitted_and_the_draft_contract(self):
		versions = frappe.db.count("Version", {"ref_doctype": "Contract", "docname": self.contract.name})

		self.edit(self.shorten, consent=True)

		for name in (self.contract.name, self.draft.name):
			_status, start, end, rows = contract_view(name)
			self.assertEqual((start, end), (START, SHORTER_END))
			self.assertEqual(rows, [(A, START, SHORTER_END, 1)])
		self.assertEqual(
			frappe.db.count("Version", {"ref_doctype": "Contract", "docname": self.contract.name}), versions + 1
		)

	def test_an_added_property_joins_the_contract_and_is_occupied(self):
		self.edit(self.add_b, consent=True)

		rows = contract_view(self.contract.name)[3]
		self.assertEqual([row[0] for row in rows], [A, B])
		self.assertEqual(fx.property_status(B), "Occupied")

	def test_unticking_the_only_row_releases_it_on_the_contract(self):
		self.edit(lambda request: setattr(request.requested_properties[0], "is_active", 0), consent=True)

		status, _start, _end, rows = contract_view(self.contract.name)
		self.assertEqual(rows[0][3], 0)
		self.assertEqual(status, "Inactive")
		self.assertEqual(fx.property_status(A), "Available")

	def test_a_row_released_on_the_contract_stays_released(self):
		self.request = fx.make_request([(B, START, END)], START, END)
		contract = fx.make_contract(self.request.name)
		fx.release_rows(contract, 0)

		self.edit(self.shorten, consent=True)

		self.assertEqual(contract_view(contract.name)[3][0][3], 0)

	def test_moving_the_start_into_the_future_reserves_the_property(self):
		future = getdate(add_months(today(), 3))

		def move(request):
			request.start_date = future
			request.end_date = getdate(add_months(future, 12))
			request.requested_properties[0].start_date = future
			request.requested_properties[0].end_date = request.end_date

		self.edit(move, consent=True)

		self.assertEqual(contract_view(self.contract.name)[0], "Inactive")
		self.assertEqual(fx.property_status(A), "Reserved")

	def test_the_synced_contract_still_cannot_be_edited_by_hand(self):
		self.edit(self.shorten, consent=True)

		contract = frappe.get_doc("Contract", self.contract.name)
		contract.end_date = END
		with self.assertRaises(frappe.ValidationError):
			contract.save(ignore_permissions=True)


class TestChecksRunFirst(ContractSyncCase):
	"""A change refused by the request's own checks leaves the Contract untouched."""

	def assert_untouched(self, change, message):
		before = contract_view(self.contract.name)

		with self.assertRaisesRegex(frappe.ValidationError, message):
			self.edit(change, consent=True)

		self.assertEqual(contract_view(self.contract.name), before)

	def test_an_overlapping_lease_is_refused(self):
		fx.make_request([(X, START, END)], START, END)

		def add_x(request):
			request.append(
				"requested_properties",
				{"utility_property": X, "item_code": X, "start_date": START, "end_date": END, "is_active": 1},
			)

		self.assert_untouched(add_x, "already leased")

	def test_a_row_outside_the_request_dates_is_refused(self):
		def outside(request):
			request.requested_properties[0].end_date = getdate(add_months(END, 1))

		self.assert_untouched(outside, "cannot be after contract end date")

	def test_a_lease_move_refusal_comes_first(self):
		with patch(f"{REQUEST_MODULE}.validate_lease_move", side_effect=frappe.ValidationError("lease move refused")):
			self.assert_untouched(self.shorten, "lease move refused")


class TestAutoRepeatUnchanged(ContractSyncCase):
	"""Under Auto Repeat a request change neither asks nor reaches the Contract."""

	approach = "Auto Repeat"

	def test_the_change_is_saved_and_the_contract_is_left_alone(self):
		before = contract_view(self.contract.name)

		self.edit(self.shorten, consent=False)
		self.edit(self.add_b, consent=False)

		self.assertEqual(contract_view(self.contract.name), before)
		request = frappe.get_doc("Utility Service Request", self.request.name)
		self.assertEqual(get_contracts_to_update(request.as_dict()), [])
