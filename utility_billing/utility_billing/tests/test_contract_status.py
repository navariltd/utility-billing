"""Tests for the status of Contracts whose property rows are released.

Under Item Price a Contract whose every row is released is Inactive: on the save
that releases the last row, after ERPNext's daily status job (through the
after_job hook) and in the daily release_ended_leases backstop. Require Contract
then refuses it. Under Auto Repeat the status stays ERPNext's, as on develop.

Every test runs in a savepoint rolled back afterwards; code that commits runs
with commits disabled.
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_months, getdate, today
from frappe.utils.background_jobs import execute_job

from utility_billing.utility_billing.overrides.server.sales_invoice import check_service_request_contract
from utility_billing.utility_billing.tests import lease_fixtures as fx
from utility_billing.utility_billing.utils import contract_status
from utility_billing.utility_billing.utils.property_status import release_ended_leases

P1 = "_Test Released Contract P1"
P2 = "_Test Released Contract P2"
P3 = "_Test Released Contract P3"
START = getdate(add_months(today(), -2)).replace(day=1)
END = getdate(add_months(START, 12))
CANCEL_AUTO_REPEATS = "utility_billing.utility_billing.overrides.server.contract.cancel_auto_repeats_for_property"
RUN_SCHEDULED_JOB = "frappe.core.doctype.scheduled_job_type.scheduled_job_type.run_scheduled_job"


def run_erpnext_status_job():
	"""Run ERPNext's daily Contract status job the way the scheduler does."""
	job_type = frappe.db.get_value("Scheduled Job Type", {"method": contract_status.ERPNEXT_STATUS_JOB}, "name")
	with fx.no_commit():
		execute_job(
			frappe.local.site,
			RUN_SCHEDULED_JOB,
			None,
			None,
			{"scheduled_job_type": job_type, "job_type": contract_status.ERPNEXT_STATUS_JOB},
			user="Administrator",
			is_async=False,
		)


class ContractStatusCase(fx.SavepointMixin, FrappeTestCase):
	approach = "Item Price"

	def setUp(self):
		super().setUp()
		fx.use_approach(self.approach)
		for name in (P1, P2, P3):
			fx.lease_property(name)

	def lease(self, *properties):
		request = fx.make_request([(name, START, END) for name in properties], START, END)
		return fx.make_contract(request.name)


class TestReleasedContractStatus(ContractStatusCase):
	"""Releasing rows on a submitted Contract, under Item Price."""

	def test_releasing_the_only_row_makes_the_contract_inactive(self):
		contract = self.lease(P1)
		self.assertEqual(contract.status, "Active")

		with patch(CANCEL_AUTO_REPEATS) as cancel:
			fx.release_rows(contract, 0)

		self.assertEqual(contract.status, "Inactive")
		self.assertEqual(fx.property_status(P1), "Available")
		cancel.assert_called_once_with(P1)

	def test_a_contract_with_an_active_row_stays_active(self):
		contract = self.lease(P1, P2)

		fx.release_rows(contract, 0)

		self.assertEqual(contract.status, "Active")
		self.assertEqual((fx.property_status(P1), fx.property_status(P2)), ("Available", "Occupied"))

	def test_releasing_the_last_of_two_rows_makes_it_inactive_and_frees_it(self):
		contract = self.lease(P1, P2)
		fx.release_rows(contract, 0)

		with patch(CANCEL_AUTO_REPEATS) as cancel:
			fx.release_rows(contract, 1)

		self.assertEqual(contract.status, "Inactive")
		self.assertEqual(fx.property_status(P2), "Available")
		cancel.assert_called_once_with(P2)

	def test_saving_a_released_contract_again_keeps_it_inactive(self):
		contract = self.lease(P1)
		fx.release_rows(contract, 0)

		contract.save(ignore_permissions=True)

		self.assertEqual(fx.contract_status(contract.name), "Inactive")

	def test_a_released_row_still_cannot_be_ticked_again(self):
		contract = self.lease(P1)
		fx.release_rows(contract, 0)

		contract.properties[0].is_active = 1
		with self.assertRaises(frappe.ValidationError):
			contract.save(ignore_permissions=True)


class TestStatusJobHook(ContractStatusCase):
	"""ERPNext's daily status job, the after_job hook and the backstop."""

	def released_and_live(self):
		released = self.lease(P1)
		fx.release_rows(released, 0)
		live = self.lease(P2)
		return released, live

	def test_erpnext_job_alone_makes_a_released_contract_active_again(self):
		released, _live = self.released_and_live()

		with fx.no_commit():
			frappe.get_attr(contract_status.ERPNEXT_STATUS_JOB)()

		self.assertEqual(fx.contract_status(released.name), "Active")

	def test_the_hook_sets_it_inactive_right_after_erpnext_job(self):
		released, live = self.released_and_live()

		run_erpnext_status_job()

		self.assertEqual(fx.contract_status(released.name), "Inactive")
		self.assertEqual(fx.contract_status(live.name), "Active")
		self.assertEqual(fx.property_status(P2), "Occupied")

	def test_the_hook_matches_the_full_path_and_the_method_name_ending(self):
		self.assertTrue(contract_status.is_erpnext_status_job(kwargs={"job_type": contract_status.ERPNEXT_STATUS_JOB}))
		self.assertTrue(
			contract_status.is_erpnext_status_job(kwargs={"job_type": "erpnext.crm.contract.update_status_for_contracts"})
		)
		self.assertTrue(contract_status.is_erpnext_status_job(method=contract_status.ERPNEXT_STATUS_JOB))
		self.assertFalse(contract_status.is_erpnext_status_job(RUN_SCHEDULED_JOB, {"job_type": "erpnext.x.other_job"}))

	def test_the_hook_finds_the_job_from_its_scheduled_job_type(self):
		job_type = frappe.db.get_value("Scheduled Job Type", {"method": contract_status.ERPNEXT_STATUS_JOB}, "name")

		self.assertTrue(contract_status.is_erpnext_status_job(RUN_SCHEDULED_JOB, {"scheduled_job_type": job_type}))

	def test_the_hook_ignores_other_jobs(self):
		released, _live = self.released_and_live()
		frappe.db.set_value("Contract", released.name, "status", "Active")

		with fx.no_commit():
			contract_status.after_scheduled_job(RUN_SCHEDULED_JOB, {"job_type": "erpnext.x.other_job"})

		self.assertEqual(fx.contract_status(released.name), "Active")

	def test_a_failure_in_the_hook_is_logged_and_rolled_back(self):
		with (
			patch.object(contract_status, "set_released_contracts_inactive", side_effect=Exception("boom")),
			patch.object(frappe.db, "rollback") as rollback,
			patch.object(frappe, "log_error") as log_error,
		):
			contract_status.after_scheduled_job(kwargs={"job_type": contract_status.ERPNEXT_STATUS_JOB})

		rollback.assert_called_once()
		log_error.assert_called_once()

	def test_release_ended_leases_sets_released_contracts_inactive_too(self):
		released, live = self.released_and_live()
		frappe.db.set_value("Contract", released.name, "status", "Active")

		release_ended_leases()

		self.assertEqual(fx.contract_status(released.name), "Inactive")
		self.assertEqual(fx.contract_status(live.name), "Active")

	def test_erpnext_status_job_is_still_registered(self):
		"""Guard: the hook matches ERPNext's job by name, so a rename must fail here."""
		self.assertTrue(callable(frappe.get_attr(contract_status.ERPNEXT_STATUS_JOB)))

		events = frappe.get_hooks("scheduler_events", app_name="erpnext")
		listed = [method for methods in events.values() if isinstance(methods, list) for method in methods]
		self.assertIn(contract_status.ERPNEXT_STATUS_JOB, listed)
		self.assertTrue(frappe.db.exists("Scheduled Job Type", {"method": contract_status.ERPNEXT_STATUS_JOB}))
		self.assertIn(
			"utility_billing.utility_billing.utils.contract_status.after_scheduled_job", frappe.get_hooks("after_job")
		)


class TestRequireContract(ContractStatusCase):
	"""Require Contract and a Contract whose every row is released."""

	def invoice_of(self, service_request):
		return frappe._dict(utility_service_request=service_request, is_return=0)

	def released(self):
		contract = self.lease(P1)
		fx.release_rows(contract, 0)
		return contract

	def test_a_released_contract_is_refused(self):
		contract = self.released()
		fx.use_approach("Item Price", require_contract=1)

		with self.assertRaisesRegex(frappe.ValidationError, "released every property"):
			check_service_request_contract(self.invoice_of(contract.utility_service_request))

	def test_a_contract_with_an_active_row_is_accepted(self):
		contract = self.lease(P1, P2)
		fx.release_rows(contract, 0)
		fx.use_approach("Item Price", require_contract=1)

		self.assertEqual(check_service_request_contract(self.invoice_of(contract.utility_service_request)), contract.name)

	def test_nothing_is_checked_with_require_contract_off(self):
		contract = self.released()

		self.assertIsNone(check_service_request_contract(self.invoice_of(contract.utility_service_request)))


class TestAutoRepeatUnchanged(ContractStatusCase):
	"""Under Auto Repeat everything stays as on develop."""

	approach = "Auto Repeat"

	def test_releasing_every_row_leaves_the_status_to_erpnext(self):
		contract = self.lease(P1)

		with patch(CANCEL_AUTO_REPEATS) as cancel:
			fx.release_rows(contract, 0)

		self.assertEqual(contract.status, "Active")
		self.assertEqual(fx.property_status(P1), "Available")
		cancel.assert_called_once_with(P1)

	def test_the_hook_and_the_backstop_write_nothing(self):
		contract = self.lease(P1)
		fx.release_rows(contract, 0)

		run_erpnext_status_job()
		release_ended_leases()

		self.assertEqual(fx.contract_status(contract.name), "Active")

	def test_require_contract_accepts_a_released_contract(self):
		contract = self.lease(P1)
		fx.release_rows(contract, 0)
		fx.use_approach("Auto Repeat", require_contract=1)

		invoice = frappe._dict(utility_service_request=contract.utility_service_request, is_return=0)
		self.assertEqual(check_service_request_contract(invoice), contract.name)


class TestPropertyAvailability(ContractStatusCase):
	"""What a Contract leaves its properties in (Part D)."""

	def move_start(self, contract, start):
		"""Move a submitted Contract's dates the way its request's sync does."""
		contract.reload()
		contract.start_date = getdate(start)
		contract.end_date = getdate(add_months(start, 12))
		for row in contract.properties:
			row.start_date, row.end_date = contract.start_date, contract.end_date
		contract.flags.from_service_request = True
		contract.flags.ignore_validate_update_after_submit = True
		contract.save(ignore_permissions=True)
		contract.reload()

	def test_cancelling_the_contract_frees_its_properties(self):
		contract = self.lease(P1)

		with patch(CANCEL_AUTO_REPEATS) as cancel:
			contract.cancel()

		self.assertEqual(fx.property_status(P1), "Available")
		cancel.assert_called_once_with(P1)

	def test_moving_the_start_into_the_future_reserves_the_property(self):
		contract = self.lease(P1)

		self.move_start(contract, add_months(today(), 3))

		self.assertEqual(contract.status, "Inactive")
		self.assertEqual(fx.property_status(P1), "Reserved")

	def test_a_released_row_is_available_even_with_a_future_start(self):
		contract = self.lease(P1, P2)
		fx.release_rows(contract, 0)

		self.move_start(contract, add_months(today(), 3))

		self.assertEqual((fx.property_status(P1), fx.property_status(P2)), ("Available", "Reserved"))


class TestPropertyAvailabilityUnderAutoRepeat(TestPropertyAvailability):
	approach = "Auto Repeat"

	def test_moving_the_start_into_the_future_reserves_the_property(self):
		contract = self.lease(P1)

		self.move_start(contract, add_months(today(), 3))

		# As on develop
		self.assertEqual(fx.property_status(P1), "Available")

	def test_a_released_row_is_available_even_with_a_future_start(self):
		contract = self.lease(P1, P2)
		fx.release_rows(contract, 0)

		self.move_start(contract, add_months(today(), 3))

		self.assertEqual((fx.property_status(P1), fx.property_status(P2)), ("Available", "Available"))
