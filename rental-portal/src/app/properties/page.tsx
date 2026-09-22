import { BaseLayout } from "@/components/layouts/base-layout";
import { PropertyListing } from "./components/property-list";

export default function PropertyList() {
  return (
    <BaseLayout
      title="Properties"
      description="Browse the units currently available for rent"
    >
      <div className="@container/main px-4 lg:px-6">
        <PropertyListing />
      </div>
    </BaseLayout>
  );
}

