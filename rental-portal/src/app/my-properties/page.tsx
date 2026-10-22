/**
 * "My Properties" – the properties linked to the signed in tenant.
 *
 * The link is the standard chain Customer (`Customer.portal_users`) → Contract
 * (`party_type = Customer`) → `Contract.properties` allocations, resolved by
 * `utility_billing.api.portal.properties.get_my_properties`. Units are shown as
 * cards or rows, sharing the presentation components with the public browser.
 */

"use client";

import { BaseLayout } from "@/components/layouts/base-layout";
import { LayoutToggle, PropertyCard, PropertyRow } from "@/components/properties";
import type { PropertyLayout, PropertyView } from "@/components/properties";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { usePageState } from "@/hooks/use-page-state";
import type { TenantProperties } from "@/types/portal";
import { useFrappeGetCall } from "frappe-react-sdk";
import { Building2 } from "lucide-react";
import { toTenantPropertyView } from "./components/tenant-property-view";

interface TenantPropertiesResponse {
  message: TenantProperties;
}

export default function MyPropertiesPage() {
  const [layout, setLayout] = usePageState<PropertyLayout>("layout", "grid");

  const { data, isLoading } = useFrappeGetCall<TenantPropertiesResponse>(
    "utility_billing.api.portal.properties.get_my_properties",
  );

  const properties = data?.message;
  const current = (properties?.current ?? []).map(toTenantPropertyView);
  const history = (properties?.history ?? []).map(toTenantPropertyView);

  return (
    <BaseLayout
      title="My Properties"
      description={
        properties?.customer
          ? `Units allocated to ${properties.customer}`
          : "Units linked to your tenancy"
      }
    >
      <div className="px-4 lg:px-6">
        <Tabs defaultValue="current">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <TabsList>
              <TabsTrigger value="current">Current ({current.length})</TabsTrigger>
              <TabsTrigger value="history">History ({history.length})</TabsTrigger>
            </TabsList>
            <LayoutToggle value={layout} onChange={setLayout} />
          </div>

          <TabsContent value="current" className="mt-4">
            <PropertyCollection
              layout={layout}
              isLoading={isLoading}
              properties={current}
              emptyMessage="You have no active or reserved units."
            />
          </TabsContent>
          <TabsContent value="history" className="mt-4">
            <PropertyCollection
              layout={layout}
              isLoading={isLoading}
              properties={history}
              emptyMessage="No past tenancies were found."
            />
          </TabsContent>
        </Tabs>
      </div>
    </BaseLayout>
  );
}

interface PropertyCollectionProps {
  layout: PropertyLayout;
  isLoading: boolean;
  properties: PropertyView[];
  emptyMessage: string;
}

function PropertyCollection({
  layout,
  isLoading,
  properties,
  emptyMessage,
}: PropertyCollectionProps) {
  if (isLoading) {
    return (
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {[1, 2].map((index) => (
          <Skeleton key={index} className="h-[320px] w-full rounded-xl" />
        ))}
      </div>
    );
  }

  if (properties.length === 0) {
    return (
      <Card>
        <CardContent className="text-muted-foreground flex flex-col items-center gap-2 py-12 text-sm">
          <Building2 className="h-6 w-6" />
          {emptyMessage}
        </CardContent>
      </Card>
    );
  }

  if (layout === "grid") {
    return (
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {properties.map((property) => (
          <PropertyCard key={property.id} property={property} />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {properties.map((property) => (
        <PropertyRow key={property.id} property={property} />
      ))}
    </div>
  );
}

