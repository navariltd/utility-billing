"""Tests for Released On, the last day a released Contract row held its property.

The release day is inclusive; a released row owns nothing after it, and nothing
at all without a date. Tests reading a stored Released On need its column,
which a migrate adds, so they are skipped before it.
"""

from unittest import skipUnless
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import getdate

from utility_billing.utility_billing.doctype.utility_service_request.utility_service_request import (
	omit_released_lines,
)
from utility_billing.utility_billing.overrides.server import sales_invoice
from utility_billing.utility_billing.report.property_wise_invoicing import property_wise_invoicing
from utility_billing.utility_billing.tests import lease_fixtures as fx
from utility_billing.utility_billing.tests.line_request_fixtures import (
	ELECTRICITY,
	P1,
	P2,
	make_invoice,
	make_price,
	make_request,
	prefill,
	setup_items,
)
from utility_billing.utility_billing.utils import auto_repeat, release
from utility_billing.utility_billing.utils.lease_overlap import validate_no_overlapping_leases
from utility_billing.utility_billing.utils.release import check_not_on_request, check_released_on, owned_period, owns

needs_column = skipUnless(
	frappe.db.has_column("Contract Utility Property Item", "released_on"), "needs Released On, which a migrate adds"
)


class TestOwnership(FrappeTestCase):
	def test_the_release_day_is_owned_and_the_next_is_not(self):
		self.assertTrue(owns("2027-01-01", "2027-12-31", "2027-05-31", True, "2027-05-31"))
		self.assertFalse(owns("2027-01-01", "2027-12-31", "2027-06-01", True, "2027-05-31"))

	def test_a_released_row_without_a_date_owns_nothing(self):
		self.assertIsNone(owned_period("2027-01-01", "2027-12-31", True, None))
		self.assertFalse(owns("2027-01-01", "2027-12-31", "2027-01-01", True, None))

	def test_a_row_still_held_owns_its_lease(self):
		self.assertEqual(owned_period("2027-01-01", "2027-12-31"), ("2027-01-01", "2027-12-31"))

	def test_an_open_lease_ends_on_its_release(self):
		self.assertEqual(owned_period("2027-01-01", None, True, "2027-03-31"), ("2027-01-01", getdate("2027-03-31")))

	def test_nothing_is_read_under_auto_repeat(self):
		with patch.object(release, "is_item_price_approach", return_value=False):
			self.assertEqual(release.contract_releases(["any"]), {})


def contract_doc(rows, start="2027-01-01", end="2027-12-31"):
	"""Return an unsaved Contract with ``rows`` of ``(is_active, released_on)``."""
	doc = frappe.new_doc("Contract")
	doc.start_date, doc.end_date = start, end
	for index, (is_active, released_on) in enumerate(rows):
		doc.append(
			"properties",
			{"name": f"row-{index}", "utility_property": P1, "is_active": is_active, "released_on": released_on},
		)
	return doc


class TestReleasedOnField(fx.SavepointMixin, FrappeTestCase):
	def setUp(self):
		super().setUp()
		fx.use_approach("Item Price")

	def test_an_active_row_cannot_have_a_date(self):
		with self.assertRaisesRegex(frappe.ValidationError, "only for a released row"):
			check_released_on(contract_doc([(1, "2027-03-01")]))

	def test_a_date_before_the_lease_is_refused(self):
		with self.assertRaisesRegex(frappe.ValidationError, "before the lease"):
			check_released_on(contract_doc([(0, "2026-12-31")]))

	def test_a_date_after_the_lease_is_refused(self):
		with self.assertRaisesRegex(frappe.ValidationError, "after the lease"):
			check_released_on(contract_doc([(0, "2028-01-01")]))

	def test_a_row_released_in_this_save_gets_today_within_its_lease(self):
		saved = contract_doc([(1, None)], start="2026-01-01", end="2027-12-31")
		doc = contract_doc([(0, None)], start="2026-01-01", end="2027-12-31")
		with patch.object(release, "nowdate", return_value="2026-11-06"):
			check_released_on(doc, saved)
		self.assertEqual(getdate(doc.properties[0].released_on), getdate("2026-11-06"))

	def test_a_row_released_after_its_lease_gets_the_lease_end(self):
		saved = contract_doc([(1, None)], start="2025-01-01", end="2025-12-31")
		doc = contract_doc([(0, None)], start="2025-01-01", end="2025-12-31")
		with patch.object(release, "nowdate", return_value="2026-11-06"):
			check_released_on(doc, saved)
		self.assertEqual(getdate(doc.properties[0].released_on), getdate("2025-12-31"))

	def test_a_row_released_before_its_lease_stays_blank(self):
		saved = contract_doc([(1, None)])
		doc = contract_doc([(0, None)])
		with patch.object(release, "nowdate", return_value="2026-11-06"):
			check_released_on(doc, saved)
		self.assertFalse(doc.properties[0].released_on)

	def test_auto_repeat_fills_no_date(self):
		fx.use_approach("Auto Repeat")
		saved = contract_doc([(1, None)], start="2026-01-01", end="2027-12-31")
		doc = contract_doc([(0, None)], start="2026-01-01", end="2027-12-31")
		check_released_on(doc, saved)
		self.assertFalse(doc.properties[0].released_on)

	def test_a_request_row_cannot_have_a_date(self):
		request = frappe._dict(requested_properties=[frappe._dict(idx=1, released_on="2027-03-01")])
		with self.assertRaisesRegex(frappe.ValidationError, "set on the Contract"):
			check_not_on_request(request)


@needs_column
class ReleasedCase(fx.SavepointMixin, FrappeTestCase):
	"""P1 leased by U1 for 2027 with Electricity; its Contract releases it on 31 May 2027."""

	def setUp(self):
		super().setUp()
		fx.use_approach("Item Price")
		setup_items()
		self.u1 = make_request([(P1, "2027-01-01", "2027-12-31")], "2027-01-01", "2028-01-01", [(ELECTRICITY, 200)])
		make_price(P1, 1000, "2027-01-01", "2027-12-31")
		self.contract = fx.make_contract(self.u1.name)
		fx.release_rows(self.contract, 0, released_on="2027-05-31")

	def govern(self, posting_date, item=P1, **line):
		invoice = make_invoice([{"item_code": item, **line}], posting_date)
		prefill(invoice)
		sales_invoice.govern_utility_lines(invoice)
		return invoice


class TestResolution(ReleasedCase):
	def test_the_release_day_is_still_billed(self):
		self.assertEqual(self.govern("2027-05-31").items[0].utility_service_request, self.u1.name)

	def test_the_day_after_is_not(self):
		with self.assertRaisesRegex(frappe.ValidationError, "leases"):
			self.govern("2027-06-01")

	def test_electricity_follows_its_property(self):
		self.assertEqual(self.govern("2027-05-10", ELECTRICITY, utility_property=P1, rate=200).items[0].rate, 200)
		with self.assertRaisesRegex(frappe.ValidationError, "leases"):
			self.govern("2027-06-10", ELECTRICITY, utility_property=P1, rate=200)


class TestRequireContract(ReleasedCase):
	def setUp(self):
		super().setUp()
		fx.use_approach("Item Price", require_contract=1, require_signed=1)

	def test_a_line_up_to_the_release_is_accepted(self):
		invoice = make_invoice([{"item_code": P1}], "2027-05-31")
		prefill(invoice)
		sales_invoice.validate(invoice)
		self.assertEqual(invoice.items[0].utility_service_request, self.u1.name)

	def test_a_line_after_the_release_is_refused_by_the_contract_too(self):
		entry = frappe._dict(row=frappe._dict(idx=1, item_code=P1), billing_date=getdate("2027-06-15"), utility_property=P1)
		with self.assertRaisesRegex(frappe.ValidationError, "released on Contract .* on 2027-05-31"):
			sales_invoice.check_within_contract(self.contract.name, [entry])


class TestOverlap(ReleasedCase):
	def new_lease(self, start):
		request = make_request([(P1, start, "2027-12-31")], start, "2028-01-01", submit=False)
		validate_no_overlapping_leases(request)

	def test_a_new_lease_after_the_release_is_allowed(self):
		self.new_lease("2027-06-01")

	def test_a_new_lease_on_the_release_day_overlaps(self):
		with self.assertRaises(frappe.ValidationError):
			self.new_lease("2027-05-31")


class TestDailyJob(ReleasedCase):
	def setUp(self):
		super().setUp()
		frappe.db.set_value(
			"Contract Utility Property Item",
			self.u1.requested_properties[0].name,
			{"enable_auto_billing": 1, "billing_date_type": "First Day of Month"},
		)
		frappe.db.sql(
			"update `tabUtility Service Request Item` set utility_property=%s where parent=%s and item_code=%s",
			(P1, self.u1.name, P1),
		)

	def drafts_on(self, day):
		with patch.object(auto_repeat, "today", return_value=day):
			auto_repeat.create_item_price_sales_invoices()
		return frappe.get_all(
			"Sales Invoice", filters={"remarks": ("like", f"%AUTO-BILLING:{self.u1.name}:%"), "posting_date": day}, pluck="name"
		)

	def test_a_month_before_the_release_is_billed(self):
		self.assertEqual(len(self.drafts_on("2027-05-01")), 1)

	def test_a_month_after_the_release_is_not(self):
		self.assertEqual(self.drafts_on("2027-06-01"), [])


class TestInvoiceFromRequest(ReleasedCase):
	def invoice(self, posting_date):
		invoice = make_invoice([{"item_code": P1, "utility_property": P1}, {"item_code": ELECTRICITY, "utility_property": P1}], posting_date)
		omit_released_lines(invoice, frappe.get_doc("Utility Service Request", self.u1.name))
		return invoice

	def test_lines_before_the_release_are_kept(self):
		self.assertEqual(len(self.invoice("2027-05-15").items), 2)

	def test_lines_after_the_release_are_left_out(self):
		with self.assertRaisesRegex(frappe.ValidationError, "released before"):
			self.invoice("2027-06-15")


class TestPropertyWiseInvoicing(ReleasedCase):
	def test_the_lease_ends_on_its_release(self):
		leases = [lease for lease in property_wise_invoicing.get_leases(frappe._dict()) if lease.service_request == self.u1.name]
		self.assertEqual([(lease.start, lease.end) for lease in leases], [(getdate("2027-01-01"), getdate("2027-05-31"))])
