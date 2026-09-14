/**
 * Property gallery – main image with a thumbnail strip.
 */

"use client";

import { PropertyMedia } from "@/components/properties";
import { cn } from "@/lib/utils";
import { useState } from "react";

interface GalleryImage {
  image: string;
  title?: string | null;
}

interface PropertyGalleryProps {
  name: string;
  coverImage?: string | null;
  gallery?: GalleryImage[];
}

export function PropertyGallery({
  name,
  coverImage,
  gallery = [],
}: PropertyGalleryProps) {
  const images = [
    ...(coverImage ? [{ image: coverImage }] : []),
    ...gallery.filter((item) => item.image && item.image !== coverImage),
  ];
  const [activeIndex, setActiveIndex] = useState(0);
  const active = images[activeIndex]?.image ?? null;

  return (
    <div className="space-y-3">
      <div className="bg-muted relative aspect-[16/10] w-full overflow-hidden rounded-xl">
        <PropertyMedia src={active} name={name} variant="cover" />
      </div>

      {images.length > 1 ? (
        <div className="flex gap-2 overflow-x-auto pb-1">
          {images.map((image, index) => (
            <button
              key={`${image.image}-${index}`}
              type="button"
              onClick={() => setActiveIndex(index)}
              aria-label={`Show image ${index + 1}`}
              className={cn(
                "h-16 w-24 shrink-0 cursor-pointer overflow-hidden rounded-lg border bg-muted transition-colors",
                index === activeIndex ? "border-primary" : "border-transparent",
              )}
            >
              <PropertyMedia src={image.image} name={name} variant="thumb" />
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}
