/**
 * Public property browser.
 *
 * Reads the guest endpoint `utility_billing.api.properties.get_available_properties`
 * and renders the results as cards (grid) or rows (list); the chosen layout is
 * remembered per page through `usePageState`.
 */

"use client";

import { LayoutToggle, PropertyCard, PropertyRow } from "@/components/properties";
import type { PropertyLayout } from "@/components/properties";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { usePageState } from "@/hooks/use-page-state";
import { useFrappeGetCall } from "frappe-react-sdk";
import { Building2, RefreshCw } from "lucide-react";
import {
  toAvailablePropertyView,
  type AvailableProperty,
} from "./available-property-view";

interface PropertiesResponse {
  message: AvailableProperty[] | { message?: AvailableProperty[]; error?: string };
}

/** The endpoint answers either with a list or with `{message: [...]}`, or with an error. */
function extractProperties(
  response: PropertiesResponse | undefined,
): AvailableProperty[] {
  const message = response?.message;
  if (!message) return [];
  if (Array.isArray(message)) return message;
  if (Array.isArray(message.message)) return message.message;
  return [];
}

export function PropertyListing() {
  const [layout, setLayout] = usePageState<PropertyLayout>("layout", "grid");

  const { data, isLoading, error, mutate } = useFrappeGetCall<PropertiesResponse>(
    "utility_billing.api.properties.get_available_properties",
    {},
    {
      revalidateOnFocus: true,
      revalidateOnReconnect: true,
    },
  );

  const properties = extractProperties(data).map(toAvailablePropertyView);

  if (error) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center gap-3 py-12 text-center">
          <Building2 className="text-muted-foreground h-8 w-8" />
          <div>
            <p className="text-destructive font-medium">Failed to load properties</p>
            <p className="text-muted-foreground text-sm">{error.message}</p>
          </div>
          <Button
            variant="outline"
            size="sm"
            className="cursor-pointer"
            onClick={() => mutate()}
          >
            <RefreshCw className="mr-2 h-4 w-4" />
            Retry
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-muted-foreground text-sm">
          {isLoading
            ? "Loading properties..."
            : `${properties.length} propert${properties.length === 1 ? "y" : "ies"} available`}
        </p>
        <LayoutToggle value={layout} onChange={setLayout} />
      </div>

      {isLoading ? (
        <PropertySkeletons layout={layout} />
      ) : properties.length === 0 ? (
        <Card>
          <CardContent className="text-muted-foreground flex flex-col items-center gap-2 py-16 text-sm">
            <Building2 className="h-8 w-8 opacity-60" />
            No properties are available at the moment.
          </CardContent>
        </Card>
      ) : layout === "grid" ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {properties.map((property) => (
            <PropertyCard key={property.id} property={property} />
          ))}
        </div>
      ) : (
        <div className="space-y-3">
          {properties.map((property) => (
            <PropertyRow key={property.id} property={property} />
          ))}
        </div>
      )}
    </div>
  );
}

function PropertySkeletons({ layout }: { layout: PropertyLayout }) {
  if (layout === "grid") {
    return (
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {[1, 2, 3, 4, 5, 6].map((index) => (
          <Skeleton key={index} className="h-[320px] w-full rounded-xl" />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {[1, 2, 3, 4].map((index) => (
        <Skeleton key={index} className="h-[120px] w-full rounded-xl" />
      ))}
    </div>
  );
}
