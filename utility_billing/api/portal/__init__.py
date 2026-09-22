"""Customer portal API for the Rental Billing (utility_billing) portal SPA.

The portal is a React SPA served from ``/rental-portal``. Its public surface is
kept deliberately small: everything that Frappe already provides
(authentication, password reset, profile and notification settings through the
generic ``/app/:doctype`` forms, notification logs, ...) is called directly from
the SPA, and this package only exposes the handful of portal specific endpoints
that the framework does not cover:

* ``utility_billing.api.portal.context`` – session/role bootstrap for the SPA.
* ``utility_billing.api.portal.properties`` – properties linked to the tenant.
"""
