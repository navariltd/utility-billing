import { BaseLayout } from "@/components/layouts/base-layout";
import { PropertyListing } from "./components/property-list";

export default function PropertyList() {
  return (
    <BaseLayout>
      <div className="flex-1 space-y-6 px-6 pt-0">
        <div className="flex md:flex-row flex-col md:items-center justify-between gap-4 md:gap-6">
          <div className="flex flex-col gap-2">
            <h1 className="text-2xl font-bold tracking-tight">
              Property Listings
            </h1>
            <p className="text-muted-foreground">
              Browse and view available properties
            </p>
          </div>
        </div>

        <div className="@container/main space-y-6">
          <PropertyListing />
        </div>
      </div>
    </BaseLayout>
  );
}
