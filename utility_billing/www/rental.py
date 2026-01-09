import json
import re

import frappe
import frappe.sessions
from frappe import _
from frappe.utils.telemetry import capture

no_cache = 1

SCRIPT_TAG_PATTERN = re.compile(r"\<script[^<]*\</script\>")
CLOSING_SCRIPT_TAG_PATTERN = re.compile(r"</script\>")


def get_context(context):
    csrf_token = frappe.sessions.get_csrf_token()
    frappe.db.commit()  # commit CSRF token

    if frappe.session.user == "Guest":
        boot = frappe.website.utils.get_boot_data()
    else:
        try:
            boot = frappe.sessions.get()
        except Exception as e:
            raise frappe.SessionBootFailed from e

    boot["push_relay_server_url"] = frappe.conf.get("push_relay_server_url")

    # server_script_enabled
    enabled = frappe.conf.get("server_script_enabled", True)
    boot["server_script_enabled"] = enabled

    boot_json = frappe.as_json(boot, indent=None, separators=(",", ":"))
    boot_json = SCRIPT_TAG_PATTERN.sub("", boot_json)
    boot_json = CLOSING_SCRIPT_TAG_PATTERN.sub("", boot_json)
    boot_json = json.dumps(boot_json)

    context.update(
        {
            "build_version": frappe.utils.get_build_version(),
            "boot": boot_json,
            "csrf_token": csrf_token,
        }
    )

    app_name = frappe.get_website_settings("app_name") or frappe.get_system_settings(
        "app_name"
    )

    if app_name and app_name != "Frappe":
        context["app_name"] = f"{app_name} | Rental Billing"
    else:
        context["app_name"] = "Rental Billing"

    favicon = frappe.get_website_settings("favicon")

    context.update(
        {
            "icon_96": favicon or "/assets/utility_billing/logo.png",
            "apple_touch_icon": favicon or "/assets/utility_billing/logo.png",
            "mask_icon": favicon or "/assets/utility_billing/logo.png",
            "favicon_svg": favicon or "/assets/utility_billing/logo.png",
            "favicon_ico": favicon or "/assets/utility_billing/logo.png",
            "sitename": boot.get("sitename"),
        }
    )

    return context


@frappe.whitelist(methods=["POST"], allow_guest=True)
def get_context_for_dev():
    if not frappe.conf.developer_mode:
        frappe.throw(_("This method is only meant for developer mode"))
    return json.loads(get_boot())


def get_boot():
    try:
        boot = frappe.sessions.get()
    except Exception as e:
        raise frappe.SessionBootFailed from e

    boot["push_relay_server_url"] = frappe.conf.get("push_relay_server_url")
    boot_json = frappe.as_json(boot, indent=None, separators=(",", ":"))
    boot_json = SCRIPT_TAG_PATTERN.sub("", boot_json)
    boot_json = CLOSING_SCRIPT_TAG_PATTERN.sub("", boot_json)
    boot_json = json.dumps(boot_json)

    return boot_json
