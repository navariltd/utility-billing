import PageBreadcrumb from "../components/common/PageBreadCrumb";
import PageMeta from "../components/common/PageMeta";
import UserInfoCard from "../components/UserProfile/UserInfoCard";
import UserMetaCard from "../components/UserProfile/UserMetaCard";

export default function UserProfiles() {
  return (
    <>
      <PageMeta
        title="User Profile | Utility Billing & Property Management"
        description="View and manage your personal details, social links, and account settings within the Utility Billing and Property Management Rental Portal."
      />

      <PageBreadcrumb pageTitle="Profile" />

      <div className="rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-white/[0.03] lg:p-6">
        <h3 className="mb-5 text-lg font-semibold text-gray-800 dark:text-white/90 lg:mb-7">
          Profile Settings
        </h3>

        <div className="space-y-6">
          {/* Displays Avatar, Name, Email, and Social Links */}
          <UserMetaCard />

          {/* Displays Detailed Personal Information form fields */}
          <UserInfoCard />

          {/* Future Addition: UserAddressCard 
            Useful for property-specific billing addresses 
          */}
          {/* <UserAddressCard /> */}
        </div>
      </div>
    </>
  );
}
