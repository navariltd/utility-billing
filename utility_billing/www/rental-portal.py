"""Context for the Rental Billing portal SPA served at ``/rental-portal``.

The SPA is bootstrapped like the other Frappe single page apps in this bench: the
standard Frappe session boot (built by ``frappe.sessions.get()``) is embedded in
the page, so the React app can read the session user and the user's roles without
an extra round trip.
"""

import json
import re

import frappe
import frappe.sessions
from frappe import _

no_cache = 1

# The boot payload is embedded inside a script tag; strip anything that could
# prematurely close it.
SCRIPT_TAG_PATTERN = re.compile(r"\<script[^<]*\</script\>")
CLOSING_SCRIPT_TAG_PATTERN = re.compile(r"</script\>")

ICON_URL = "/assets/utility_billing/logo.png"


def get_context(context):
	context.update(_get_page_context())
	return context


@frappe.whitelist(methods=["POST"], allow_guest=True)
def get_context_for_dev():
	"""Return the boot payload for local (Vite) development."""
	if not frappe.conf.developer_mode:
		frappe.throw(_("This method is only meant for developer mode"))

	return _get_boot()


def _get_page_context() -> dict:
	"""Build the template context for the portal page."""
	boot = _get_boot()
	app_name = frappe.get_website_settings("app_name") or frappe.get_system_settings("app_name")

	return {
		"boot": _serialize_boot(boot),
		"csrf_token": frappe.sessions.get_csrf_token(),
		"app_name": f"{app_name} | Rental Portal" if app_name and app_name != "Frappe" else "Rental Portal",
		"icon_96": ICON_URL,
		"apple_touch_icon": ICON_URL,
		"mask_icon": ICON_URL,
		"favicon_svg": ICON_URL,
		"favicon_ico": ICON_URL,
		"sitename": boot.get("sitename") or frappe.local.site,
		"preload_links": "",
	}


def _get_boot() -> dict:
	"""Return the Frappe boot payload for the current session."""
	if frappe.session.user == "Guest":
		return frappe.website.utils.get_boot_data()

	try:
		return frappe.sessions.get()
	except Exception as e:
		raise frappe.SessionBootFailed from e


def _serialize_boot(boot: dict) -> str:
	"""Serialize the boot payload for embedding as ``JSON.parse(<payload>)``."""
	boot_json = frappe.as_json(boot, indent=None, separators=(",", ":"))
	boot_json = SCRIPT_TAG_PATTERN.sub("", boot_json)
	boot_json = CLOSING_SCRIPT_TAG_PATTERN.sub("", boot_json)

	return json.dumps(boot_json)

