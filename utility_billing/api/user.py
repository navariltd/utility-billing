import frappe

@frappe.whitelist()
def get_user_details() -> dict:
    name = frappe.session.user
    user = frappe.get_doc("User", name)
    return user.as_dict()