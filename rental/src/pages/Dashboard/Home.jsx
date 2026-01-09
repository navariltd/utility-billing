import PageMeta from "../../components/common/PageMeta";

export default function Home() {
  return (
    <>
      <PageMeta
        title="Rental Portal | Utility Billing & Property Management"
        description="Access your rental dashboard to manage utility bills, property leases, and tenant information. Streamlined property management powered by ERPNext."
      />

      <div className="grid grid-cols-12 gap-4 md:gap-6">
        {/* Dashboard content goes here */}
      </div>
    </>
  );
}
