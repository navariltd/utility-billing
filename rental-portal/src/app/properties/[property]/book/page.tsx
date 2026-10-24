/**
 * Unit booking page.
 *
 * The wizard collects the lease dates and tenant details, then creates the
 * Utility Service Request that reserves the unit.
 */

import { BaseLayout } from "@/components/layouts/base-layout";
import { useParams } from "react-router-dom";
import { BookingWizard } from "./components/booking-wizard";

export default function PropertyBooking() {
  const { property } = useParams<{ property: string }>();
  const propertyName = property ? decodeURIComponent(property) : "";

  return (
    <BaseLayout
      title={`Book ${propertyName || "property"}`}
      description="Reserve this unit"
    >
      <div className="mx-auto w-full max-w-3xl px-4 lg:px-6">
        {propertyName ? <BookingWizard property={propertyName} /> : null}
      </div>
    </BaseLayout>
  );
}

