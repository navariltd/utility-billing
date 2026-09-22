/**
 * Property details page.
 *
 * Shows the property (gallery, description, amenities, specifications) with a
 * booking action when the unit is available, and — for the tenant of the unit —
 * the tenancy summary plus every related document: Sales Invoices, Sales Orders,
 * Payment Entries, Meter Readings and Utility Service Requests.
 *
 * All data comes from a single endpoint,
 * `utility_billing.api.portal.property_details.get_property_details`, which
 * enforces the access rules server side.
 */

"use client";

import { BaseLayout } from "@/components/layouts/base-layout";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { PropertyDetailsPayload } from "@/types/property-details";
import { useFrappeGetCall } from "frappe-react-sdk";
import { SearchX } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { PropertyDocumentsView } from "./components/property-documents";
import { PropertyGallery } from "./components/property-gallery";
import { PropertyOverview } from "./components/property-overview";
import { PropertySidePanel } from "./components/property-side-panel";

interface PropertyDetailsResponse {
  message: PropertyDetailsPayload;
}

export default function PropertyDetailsPage() {
  const { property } = useParams<{ property: string }>();
  const propertyName = property ? decodeURIComponent(property) : "";

  const { data, isLoading, error } = useFrappeGetCall<PropertyDetailsResponse>(
    "utility_billing.api.portal.property_details.get_property_details",
    { property: propertyName },
    propertyName ? `property-details-${propertyName}` : null,
  );

  const payload = data?.message;

  if (propertyName && isLoading && !payload) {
    return (
      <BaseLayout title="Property">
        <div className="grid gap-6 px-4 lg:grid-cols-3 lg:px-6">
          <div className="space-y-4 lg:col-span-2">
            <Skeleton className="aspect-[16/10] w-full rounded-xl" />
            <Skeleton className="h-40 w-full rounded-xl" />
          </div>
          <Skeleton className="h-64 w-full rounded-xl" />
        </div>
      </BaseLayout>
    );
  }

  if (error || !payload) {
    const isForbidden =
      error?.httpStatus === 403 ||
      error?.exception === "frappe.exceptions.PermissionError";

    return (
      <BaseLayout
        title={isForbidden ? "Property unavailable" : "Property not found"}
        description={
          isForbidden
            ? "This unit is not open for public viewing."
            : "We could not load this property."
        }
      >
        <div className="px-4 lg:px-6">
          <Card>
            <CardContent className="text-muted-foreground flex flex-col items-center gap-3 py-16 text-center text-sm">
              <SearchX className="h-6 w-6" />
              {isForbidden
                ? "This unit is occupied or reserved, and it is not linked to your account."
                : error?.message || "Please check the address and try again."}
              <div className="flex gap-2">
                <Button asChild variant="outline" size="sm" className="cursor-pointer">
                  <Link to="/properties">Browse available properties</Link>
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </BaseLayout>
    );
  }

  const { property: details, documents, is_mine } = payload;

  return (
    <BaseLayout
      title={details.property_name || details.name}
      description={
        is_mine ? "Your unit, documents and account summary" : "Property details"
      }
    >
      <div className="grid gap-6 px-4 lg:grid-cols-3 lg:px-6">
        <div className="space-y-6 lg:col-span-2">
          <PropertyGallery
            name={details.property_name || details.name}
            coverImage={details.cover_image}
            gallery={details.image_gallery}
          />
          <PropertyOverview property={details} />

          {is_mine && documents ? (
            <div className="space-y-3">
              <h2 className="text-lg font-semibold">Related documents</h2>
              <PropertyDocumentsView documents={documents} />
            </div>
          ) : null}
        </div>

        <PropertySidePanel payload={payload} />
      </div>
    </BaseLayout>
  );
}
