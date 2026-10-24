/**
 * Property gallery – large image box with captions, arrows and thumbnails.
 *
 * The main image opens a full-screen viewer where tenants can read each
 * picture's title and description and move through the gallery with the
 * on-screen arrows or the keyboard.
 */

"use client";

import { PropertyMedia } from "@/components/properties";
import { cn } from "@/lib/utils";
import { ChevronLeft, ChevronRight, Expand } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { PropertyLightbox, type LightboxImage } from "./property-lightbox";

interface PropertyGalleryProps {
  name: string;
  coverImage?: string | null;
  gallery?: LightboxImage[];
}

export function PropertyGallery({
  name,
  coverImage,
  gallery = [],
}: PropertyGalleryProps) {
  const images: LightboxImage[] = [
    ...(coverImage ? [{ image: coverImage, title: name }] : []),
    ...gallery.filter((item) => item.image && item.image !== coverImage),
  ];
  const total = images.length;
  const [activeIndex, setActiveIndex] = useState(0);
  const [viewerIndex, setViewerIndex] = useState<number | null>(null);

  const active = images[activeIndex];
  const activeNumber = total === 0 ? 0 : activeIndex + 1;

  const step = useCallback(
    (direction: number) => {
      if (total === 0) {
        return;
      }

      setActiveIndex((current) => (current + direction + total) % total);
    },
    [total],
  );

  const syncIndex = useCallback((index: number) => {
    setActiveIndex(index);
    setViewerIndex(index);
  }, []);

  useEffect(() => {
    if (viewerIndex === null) {
      return;
    }

    const handler = (event: KeyboardEvent) => {
      if (event.key === "ArrowRight") {
        step(1);
      } else if (event.key === "ArrowLeft") {
        step(-1);
      }
    };

    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [step, viewerIndex]);

  return (
    <div className="space-y-3">
      <div className="group bg-muted relative aspect-[16/10] w-full overflow-hidden rounded-xl">
        {active ? (
          <button
            type="button"
            onClick={() => syncIndex(activeIndex)}
            aria-label="Open image viewer"
            className="absolute inset-0 h-full w-full cursor-zoom-in"
          >
            <PropertyMedia src={active.image} name={active.title || name} variant="cover" />
            <span className="pointer-events-none absolute inset-0 bg-gradient-to-t from-black/60 via-black/10 to-transparent" />
          </button>
        ) : (
          <PropertyMedia src={null} name={name} variant="cover" />
        )}

        {active ? (
          <div className="pointer-events-none absolute inset-x-0 bottom-0 space-y-1 p-4 text-white">
            {active.title ? (
              <p className="text-base font-semibold drop-shadow-sm">{active.title}</p>
            ) : null}
            {active.description ? (
              <p className="line-clamp-2 max-w-2xl text-sm text-white/85">
                {active.description}
              </p>
            ) : null}
          </div>
        ) : null}

        {total > 1 ? (
          <>
            <GalleryArrow side="left" onClick={() => step(-1)} label="Previous image" />
            <GalleryArrow side="right" onClick={() => step(1)} label="Next image" />
            <span className="pointer-events-none absolute top-3 right-3 rounded-full bg-black/60 px-2.5 py-1 text-xs font-medium text-white">
              {activeNumber} / {total}
            </span>
          </>
        ) : null}

        {active ? (
          <button
            type="button"
            onClick={() => syncIndex(activeIndex)}
            aria-label="View full size"
            className="absolute top-3 left-3 cursor-pointer rounded-full bg-black/60 p-2 text-white transition-colors hover:bg-black/80"
          >
            <Expand className="h-4 w-4" />
          </button>
        ) : null}
      </div>

      {total > 1 ? (
        <div className="flex gap-2 overflow-x-auto pb-1">
          {images.map((image, index) => (
            <button
              key={`${image.image}-${index}`}
              type="button"
              onClick={() => setActiveIndex(index)}
              onDoubleClick={() => syncIndex(index)}
              aria-label={image.title || `Show image ${index + 1}`}
              aria-current={index === activeIndex}
              title={image.title || undefined}
              className={cn(
                "bg-muted h-16 w-24 shrink-0 cursor-pointer overflow-hidden rounded-lg border-2 transition-colors",
                index === activeIndex
                  ? "border-primary"
                  : "border-transparent opacity-80 hover:opacity-100",
              )}
            >
              <PropertyMedia src={image.image} name={image.title || name} variant="thumb" />
            </button>
          ))}
        </div>
      ) : null}

      <PropertyLightbox
        name={name}
        images={images}
        index={viewerIndex}
        onIndexChange={syncIndex}
        onClose={() => setViewerIndex(null)}
      />
    </div>
  );
}

interface GalleryArrowProps {
  side: "left" | "right";
  label: string;
  onClick: () => void;
}

function GalleryArrow({ side, label, onClick }: GalleryArrowProps) {
  const Icon = side === "left" ? ChevronLeft : ChevronRight;

  return (
    <button
      type="button"
      onClick={(event) => {
        event.stopPropagation();
        onClick();
      }}
      aria-label={label}
      className={cn(
        "absolute top-1/2 z-10 -translate-y-1/2 cursor-pointer rounded-full bg-black/50 p-2 text-white opacity-0 transition-all hover:bg-black/70 focus-visible:opacity-100 group-hover:opacity-100",
        side === "left" ? "left-3" : "right-3",
      )}
    >
      <Icon className="h-5 w-5" />
    </button>
  );
}

