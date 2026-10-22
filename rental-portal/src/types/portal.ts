/**
 * Types shared by the rental portal authentication, profile and property views.
 */

/** Capabilities granted to a portal role by `utility_billing.api.portal.context`. */
export type PortalCapability =
  | "browse_properties"
  | "view_dashboard"
  | "view_my_units"
  | "manage_profile"
  | "manage_notifications";

export const PORTAL_CAPABILITIES: PortalCapability[] = [
  "browse_properties",
  "view_dashboard",
  "view_my_units",
  "manage_profile",
  "manage_notifications",
];

/** Portal role names resolved on the server. */
export const GUEST_ROLE = "Guest";
export const TENANT_ROLE = "Tenant";
export const LANDLORD_ROLE = "Property Owner";
export const MANAGER_ROLE = "Property Manager";
export const UTILITY_CUSTOMER_ROLE = "Utility Customer";

/** Customer a portal user is linked to through `Customer.portal_users`. */
export interface PortalCustomer {
  name: string;
  customer_name: string;
}

/** Payload returned by `utility_billing.api.portal.context.get_portal_context`. */
export interface PortalContextData {
  user: string;
  full_name: string;
  email: string | null;
  user_image: string | null;
  language: string | null;
  time_zone: string | null;
  roles: string[];
  portal_role: string;
  customer: string | null;
  customers: PortalCustomer[];
  capabilities: Record<PortalCapability, boolean>;
}

/** The subset of `frappe.boot.user` consumed by the portal. */
export interface BootUser {
  name: string;
  full_name?: string;
  email?: string;
  user_image?: string;
  user_type?: string;
  language?: string;
  time_zone?: string;
  roles?: string[];
}

/** Session user exposed by the portal user context. */
export interface PortalUser {
  name: string;
  fullName: string;
  email: string | null;
  userImage: string | null;
  userType: string | null;
  language: string | null;
  timeZone: string | null;
  /** Frappe roles taken from the session boot. */
  roles: string[];
  /** Portal role resolved by the server (Tenant, Property Manager, ...). */
  portalRole: string;
}

/** A single property allocation of the tenant (`get_my_properties`). */
export interface TenantProperty {
  utility_property: string;
  property_name: string;
  utility_category: string | null;
  company: string | null;
  location: string | null;
  territory: string | null;
  house_no: string | null;
  plot_no: string | null;
  unit_number: string | null;
  unit_type: string | null;
  bedrooms: number | null;
  bathrooms: number | null;
  unit_size: number | null;
  floor_level: string | null;
  cover_image: string | null;
  parent_utility_property: string | null;
  state: "Active" | "Reserved" | "History";
  contract: string;
  contract_status: string | null;
  is_signed: number;
  start_date: string | null;
  end_date: string | null;
  contract_length_months: number | null;
  insurance: string | null;
}

/** Payload returned by `utility_billing.api.portal.properties.get_my_properties`. */
export interface TenantProperties {
  customer: string | null;
  current: TenantProperty[];
  history: TenantProperty[];
}
