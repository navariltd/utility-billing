"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useFrappeGetCall } from "frappe-react-sdk";
import {
  AlertCircle,
  Bath,
  Bed,
  Building2,
  CheckCircle,
  Clock,
  DollarSign,
  Eye,
  Home,
  Layers,
  MapPin,
  Square,
} from "lucide-react";

interface PropertyFeature {
  feature: string;
  feature_type?: string;
  notes?: string;
}

interface GalleryImage {
  image: string;
  title: string;
  description: string;
}

interface UtilityProperty {
  name: string;
  property_name: string;
  utility_category: string;
  company: string;
  status: "Available" | "Occupied" | "Under Maintenance" | "Reserved";
  is_fixed_asset: boolean;
  is_group: boolean;
  location: string;
  territory: string;
  house_no: string;
  plot_no: string;
  lot_size: string;
  unit_number: string;
  bedrooms: number;
  bathrooms: number;
  unit_type: string;
  unit_size: number;
  floor_level: string;
  cover_image?: string;
  image_gallery?: GalleryImage[];
  features?: PropertyFeature[];
  unique_features?: string;
  legal_description?: string;
  asset_category?: string;
  purchase_date?: string;
  net_purchase_amount?: number;
  parent_utility_property?: string;
}

interface ApiResponse {
  message: UtilityProperty[] | { message?: UtilityProperty[]; error?: string };
}

export function PropertyListing() {
  const {
    data: propertiesData,
    isLoading,
    error,
    mutate,
  } = useFrappeGetCall<ApiResponse>(
    "utility_billing.api.properties.get_available_properties",
    {},
    {
      revalidateOnFocus: true,
      revalidateOnReconnect: true,
    },
  );

  let properties: UtilityProperty[] = [];

  if (propertiesData?.message) {
    if (Array.isArray(propertiesData.message)) {
      properties = propertiesData.message;
    } else if (
      propertiesData.message &&
      typeof propertiesData.message === "object"
    ) {
      if (
        propertiesData.message.message &&
        Array.isArray(propertiesData.message.message)
      ) {
        properties = propertiesData.message.message;
      } else if ("error" in propertiesData.message) {
        console.error("API returned error:", propertiesData.message.error);
      }
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case "Available":
        return "bg-green-100 text-green-800 border-green-200";
      case "Occupied":
        return "bg-blue-100 text-blue-800 border-blue-200";
      case "Under Maintenance":
        return "bg-orange-100 text-orange-800 border-orange-200";
      case "Reserved":
        return "bg-pink-100 text-pink-800 border-pink-200";
      default:
        return "bg-gray-100 text-gray-800 border-gray-200";
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "Available":
        return <CheckCircle className="h-4 w-4" />;
      case "Occupied":
        return <Home className="h-4 w-4" />;
      case "Under Maintenance":
        return <Clock className="h-4 w-4" />;
      case "Reserved":
        return <AlertCircle className="h-4 w-4" />;
      default:
        return null;
    }
  };

  if (isLoading) {
    return (
      <Card className="cursor-pointer">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
          <div>
            <CardTitle>Properties</CardTitle>
            <CardDescription>Loading properties...</CardDescription>
          </div>
          <Button
            variant="outline"
            size="sm"
            className="cursor-pointer"
            disabled
          >
            <Eye className="h-4 w-4 mr-2" />
            Loading...
          </Button>
        </CardHeader>
        <CardContent className="space-y-4">
          {[1, 2, 3, 4, 5].map((i) => (
            <div
              key={i}
              className="flex items-center p-3 rounded-lg border gap-4"
            >
              <Skeleton className="h-12 w-12 rounded-full" />
              <div className="flex-1 space-y-2">
                <Skeleton className="h-4 w-3/4" />
                <Skeleton className="h-3 w-1/2" />
              </div>
              <div className="text-right space-y-2">
                <Skeleton className="h-4 w-24" />
                <Skeleton className="h-3 w-16" />
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="cursor-pointer">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
          <div>
            <CardTitle className="text-red-600">
              Error Loading Properties
            </CardTitle>
            <CardDescription>
              {error.message || "Failed to load properties"}
            </CardDescription>
          </div>
          <Button
            variant="outline"
            size="sm"
            className="cursor-pointer"
            onClick={() => mutate()}
          >
            <Eye className="h-4 w-4 mr-2" />
            Retry
          </Button>
        </CardHeader>
      </Card>
    );
  }

  if (!properties || properties.length === 0) {
    return (
      <Card className="cursor-pointer">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
          <div>
            <CardTitle>Properties</CardTitle>
            <CardDescription>No properties found</CardDescription>
          </div>
          <Button variant="outline" size="sm" className="cursor-pointer">
            <Eye className="h-4 w-4 mr-2" />
            View All
          </Button>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8 text-muted-foreground">
            <Building2 className="h-12 w-12 mx-auto mb-3 opacity-50" />
            <p>No properties available at the moment.</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="cursor-pointer">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
        <div>
          <CardTitle>Properties</CardTitle>
          <CardDescription>
            {properties.length} properties available
          </CardDescription>
        </div>
        <Button variant="outline" size="sm" className="cursor-pointer">
          <Eye className="h-4 w-4 mr-2" />
          View All
        </Button>
      </CardHeader>
      <CardContent className="space-y-4">
        {properties.map((property, index) => (
          <div
            key={property.name || index}
            className="flex items-start p-3 rounded-lg border hover:bg-accent/50 transition-colors gap-3"
          >
            <div className="flex-shrink-0">
              {property.cover_image ? (
                <div className="w-12 h-12 rounded-lg overflow-hidden bg-muted">
                  <img
                    src={property.cover_image}
                    alt={property.property_name}
                    className="w-full h-full object-cover"
                    loading="lazy"
                    onError={(e) => {
                      (e.target as HTMLImageElement).style.display = "none";
                    }}
                  />
                </div>
              ) : (
                <div className="flex items-center justify-center w-12 h-12 rounded-lg bg-primary/10 text-primary">
                  <Building2 className="h-6 w-6" />
                </div>
              )}
            </div>

            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between flex-wrap gap-2">
                <div className="flex items-center space-x-2">
                  <h3 className="text-sm font-medium truncate">
                    {property.property_name || "Unnamed Property"}
                  </h3>
                  <Badge
                    variant="outline"
                    className={`${getStatusColor(property.status)} border-0 cursor-pointer`}
                  >
                    {getStatusIcon(property.status)}
                    <span className="ml-1">{property.status || "Unknown"}</span>
                  </Badge>
                </div>

                {property.net_purchase_amount && (
                  <div className="flex items-center space-x-1 text-sm font-medium text-green-600">
                    <DollarSign className="h-3 w-3" />
                    {property.net_purchase_amount.toLocaleString()}
                  </div>
                )}
              </div>

              {(property.location ||
                property.territory ||
                property.house_no) && (
                <div className="flex items-center space-x-2 mt-1 text-xs text-muted-foreground">
                  <MapPin className="h-3 w-3 flex-shrink-0" />
                  <span className="truncate">
                    {[
                      property.house_no,
                      property.plot_no,
                      property.location,
                      property.territory,
                    ]
                      .filter(Boolean)
                      .join(", ")}
                  </span>
                </div>
              )}

              <div className="flex flex-wrap items-center gap-2 mt-1.5">
                {property.utility_category && (
                  <Badge variant="secondary" className="text-xs">
                    {property.utility_category}
                  </Badge>
                )}

                {property.unit_type && (
                  <Badge variant="outline" className="text-xs">
                    <Layers className="h-3 w-3 mr-1" />
                    {property.unit_type}
                  </Badge>
                )}

                {property.bedrooms && (
                  <span className="flex items-center text-xs text-muted-foreground">
                    <Bed className="h-3 w-3 mr-1" />
                    {property.bedrooms}
                  </span>
                )}

                {property.bathrooms && (
                  <span className="flex items-center text-xs text-muted-foreground">
                    <Bath className="h-3 w-3 mr-1" />
                    {property.bathrooms}
                  </span>
                )}

                {property.unit_size && (
                  <span className="flex items-center text-xs text-muted-foreground">
                    <Square className="h-3 w-3 mr-1" />
                    {property.unit_size} sqft
                  </span>
                )}

                {property.floor_level && (
                  <span className="flex items-center text-xs text-muted-foreground">
                    <Building2 className="h-3 w-3 mr-1" />
                    {property.floor_level}
                  </span>
                )}

                {property.is_fixed_asset && (
                  <Badge
                    variant="outline"
                    className="text-xs text-blue-600 border-blue-200"
                  >
                    Fixed Asset
                  </Badge>
                )}

                {property.is_group && (
                  <Badge
                    variant="outline"
                    className="text-xs text-purple-600 border-purple-200"
                  >
                    Group
                  </Badge>
                )}
              </div>

              {property.features && property.features.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-1.5">
                  {property.features.slice(0, 3).map((feature, idx) => (
                    <Badge
                      key={idx}
                      variant="ghost"
                      className="text-xs bg-muted/50"
                    >
                      {feature.feature}
                    </Badge>
                  ))}
                  {property.features.length > 3 && (
                    <Badge variant="ghost" className="text-xs bg-muted/50">
                      +{property.features.length - 3} more
                    </Badge>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
