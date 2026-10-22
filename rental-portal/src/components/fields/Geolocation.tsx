"use client";

import { cn } from "@/lib/utils";
import { MapPin } from "lucide-react";
import * as React from "react";

interface GeolocationProps {
  value: { latitude: number; longitude: number } | null;
  onChange: (val: { latitude: number; longitude: number } | null) => void;
  onBlur?: () => void;
  className?: string;
  disabled?: boolean;
  required?: boolean;
  label?: string;
}

export const Geolocation = ({
  value = null,
  onChange,
  onBlur,
  className = "",
  disabled = false,
  required = false,
  label,
}: GeolocationProps) => {
  const [latitude, setLatitude] = React.useState(
    value?.latitude?.toString() || "",
  );
  const [longitude, setLongitude] = React.useState(
    value?.longitude?.toString() || "",
  );

  const handleGetLocation = () => {
    if (!navigator.geolocation) {
      alert("Geolocation is not supported by your browser");
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const lat = position.coords.latitude;
        const lng = position.coords.longitude;
        setLatitude(lat.toString());
        setLongitude(lng.toString());
        onChange({ latitude: lat, longitude: lng });
      },
      (error) => {
        console.error(error);
        alert("Failed to get location: " + error.message);
      },
    );
  };

  const handleLatChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setLatitude(val);
    const lat = parseFloat(val);
    const lng = parseFloat(longitude);
    if (!isNaN(lat) && !isNaN(lng)) {
      onChange({ latitude: lat, longitude: lng });
    } else if (!val) {
      onChange(null);
    }
  };

  const handleLngChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setLongitude(val);
    const lat = parseFloat(latitude);
    const lng = parseFloat(val);
    if (!isNaN(lat) && !isNaN(lng)) {
      onChange({ latitude: lat, longitude: lng });
    } else if (!val) {
      onChange(null);
    }
  };

  return (
    <div className={cn("w-full flex flex-col gap-1.5", className)}>
      {label && (
        <label className="text-sm font-medium text-foreground flex items-center gap-0.5 select-none">
          {label}
          {required && (
            <span className="text-destructive font-bold text-red-500 ml-0.5">
              *
            </span>
          )}
        </label>
      )}
      <div className="flex gap-2">
        <div className="flex-1">
          <input
            type="text"
            value={latitude}
            onChange={handleLatChange}
            onBlur={onBlur}
            disabled={disabled}
            placeholder="Latitude"
            className={cn(
              "flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-xs transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50",
              className,
            )}
          />
        </div>
        <div className="flex-1">
          <input
            type="text"
            value={longitude}
            onChange={handleLngChange}
            onBlur={onBlur}
            disabled={disabled}
            placeholder="Longitude"
            className={cn(
              "flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-xs transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50",
              className,
            )}
          />
        </div>
        <button
          type="button"
          onClick={handleGetLocation}
          disabled={disabled}
          className={cn(
            "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 border border-input bg-background shadow-sm hover:bg-accent hover:text-accent-foreground h-9 px-4 py-2",
          )}
        >
          <MapPin className="size-4" />
        </button>
      </div>
    </div>
  );
};
