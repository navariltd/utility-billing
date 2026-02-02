app_name = "utility_billing"
app_title = "Utility & Rental Billing"
app_publisher = "Navari Ltd"
app_description = "Utility Billing & Property Management"
app_email = "support@navari.co.ke"
app_license = "agpl-3.0"

fixtures = [
    {
        "doctype": "Item Group",
        "or_filters": [
            ["name", "in", ["Utility and Rental"]],
            ["parent_item_group", "in", ["Utility and Rental"]],
        ],
    }
]

accounting_dimension_doctypes = [
    "Utility Bill Structure",
    "Utility Service Request",
    "Utility Service Request Item",
    "Meter Reading",
]


# Apps
# ------------------

required_apps = ["erpnext", "crm"]

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
add_to_apps_screen = [
    {
        "name": "rental",
        "logo": "/assets/utility_billing/logo.png",
        "title": "Rental Billing",
        "route": "/rental",
        "has_permission": "utility_billing.permissions.check_app_permission",
    }
]
# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/utility_billing/css/utility_billing.css"
app_include_js = "/assets/utility_billing/js/demo.js"

# include js, css files in header of web template
# web_include_css = "/assets/utility_billing/css/utility_billing.css"
# web_include_js = "/assets/utility_billing/js/utility_billing.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "utility_billing/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
    "Item Price": "utility_billing/overrides/client/item_price.js",
    "Contract": "utility_billing/overrides/client/contract.js",
    "Auto Repeat": "utility_billing/overrides/client/auto_repeat.js",
}
# doctype_js = {"Customer": "utility_billing/overrides/client/customer.js"}
doctype_list_js = {
    "Sales Order": "utility_billing/overrides/client/sales_order_list.js",
    "Auto Repeat": "utility_billing/overrides/client/auto_repeat_list.js",
}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "utility_billing/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "utility_billing.utils.jinja_methods",
# 	"filters": "utility_billing.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "utility_billing.install.before_install"
# after_install = "utility_billing.setup.install.create_utility_property_dimension"

# Uninstallation
# ------------

# before_uninstall = "utility_billing.uninstall.before_uninstall"
# after_uninstall = "utility_billing.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "utility_billing.utils.before_app_install"

utility_demo_master_doctypes = [
    "billing_adjustment_rule",
    "contract_template",
    "customer_group",
    "customer",
    "insurance_type",
    "supplier",
    "insurance",
    "issue_type",
    "item_group",
    "item",
    "price_list",
    "utility_tariff_block",
    "item_price",
    "location",
    "serial_no",
    "uom",
    "utility_property_feature_type",
    "utility_property_feature",
    "utility_property_unit_type",
    "utility_category",
    "warranty_claim",
    "asset_category",
    "utility_property",
]


# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "utility_billing.utils.before_app_uninstall"
# after_app_uninstall = "utility_billing.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "utility_billing.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
    # "*": {
    # 	"on_update": "method",
    # 	"on_cancel": "method",
    # 	"on_trash": "method"
    # }
    "Sales Order": {
        "validate": [
            "utility_billing.utility_billing.overrides.server.sales_order.validate"
        ],
    },
    "Sales Invoice": {
        "before_validate": [
            "utility_billing.utility_billing.overrides.server.sales_invoice.before_validate"
        ],
        "validate": [
            "utility_billing.utility_billing.overrides.server.sales_invoice.validate"
        ],
        "on_submit": [
            "utility_billing.utility_billing.overrides.server.sales_invoice.on_submit"
        ],
    },
    "Contract": {
        "before_submit": [
            "utility_billing.utility_billing.overrides.server.contract.before_submit"
        ],
        "on_cancel": [
            "utility_billing.utility_billing.overrides.server.contract.on_cancel"
        ],
        "on_update_after_submit": [
            "utility_billing.utility_billing.overrides.server.contract.on_update_after_submit"
        ],
        "on_submit": [
            "utility_billing.utility_billing.overrides.server.contract.on_submit"
        ],
    },
    "Auto Repeat": {
        "on_update": [
            "utility_billing.utility_billing.overrides.server.auto_repeat.on_update"
        ],
    },
    "Item": {
        "validate": ["utility_billing.utility_billing.overrides.server.item.validate"],
    },
}

# Scheduled Tasks
# ---------------

scheduler_events = {
    # "cron": {
    #     "*/1 * * * *": [
    #         "utility_billing.utility_billing.utils.auto_repeat.process_penalties_for_overdue_invoices"
    #     ]
    # },
    "daily": [
        "utility_billing.utility_billing.utils.auto_repeat.process_penalties_for_overdue_invoices",
        "utility_billing.utility_billing.overrides.server.auto_repeat.run_all_due_auto_repeats",
    ],
    # 	"hourly": [
    # 		"utility_billing.tasks.hourly"
    # 	],
    # 	"weekly": [
    # 		"utility_billing.tasks.weekly"
    # 	],
    # 	"monthly": [
    # 		"utility_billing.tasks.monthly"
    # 	],
}

# Testing
# -------

# before_tests = "utility_billing.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "utility_billing.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "utility_billing.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["utility_billing.utils.before_request"]
# after_request = ["utility_billing.utils.after_request"]

# Job Events
# ----------
# before_job = ["utility_billing.utils.before_job"]
# after_job = ["utility_billing.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"utility_billing.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }


website_route_rules = [
    {"from_route": "/rental", "to_route": "rental"},
    {"from_route": "/rental/<path:app_path>", "to_route": "rental"},
]
