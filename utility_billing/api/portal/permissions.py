"""Permission scope for documents the portal provisions for a tenant.

Portal endpoints already enforce ownership in code (the caller's Customer and
the caller's own requests), so framework permission checks are bypassed while
the portal creates the underlying documents. This keeps a first-time tenant
without desk roles from being blocked by the portal's own automation.
"""

from collections.abc import Iterator
from contextlib import contextmanager

import frappe


@contextmanager
def ignore_permissions() -> Iterator[None]:
	"""Temporarily enable ``frappe.flags.ignore_permissions``."""
	previous = getattr(frappe.flags, "ignore_permissions", False)
	frappe.flags.ignore_permissions = True
	try:
		yield
	finally:
		frappe.flags.ignore_permissions = previous
