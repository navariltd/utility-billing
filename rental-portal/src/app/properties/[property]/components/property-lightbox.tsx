/**
 * Full-screen property image viewer.
 *
 * Opens over the details page, keeps the gallery order, and shows each image's
 * title and description. Arrow keys, the on-screen arrows and the thumbnail
 * strip all move between images; Escape closes the viewer.
 */

"use client";

import { PropertyMedia } from "@/components/properties";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { cn } from "@/lib/utils";
import { ChevronLeft, ChevronRight, X } from "lucide-react";
import { useCallback, useEffect } from "react";

export interface LightboxImage {
  image: string;
  title?: string | null;
  description?: string | null;
}

interface PropertyLightboxProps {
  name: string;
  images: LightboxImage[];
  /** Active image index, or `null` when the viewer is closed. */
  index: number | null;
  onIndexChange: (index: number) => void;
  onClose: () => void;
}

export function PropertyLightbox({
  name,
  images,
  index,
  onIndexChange,
  onClose,
}: PropertyLightboxProps) {
  const open = index !== null && images.length > 0;
  const total = images.length;

  const go = useCallback(
    (step: number) => {
      if (index === null || total === 0) {
        return;
      }

      onIndexChange((index + step + total) % total);
    },
    [index, onIndexChange, total],
  );

  useEffect(() => {
    if (!open) {
      return;
    }

    const handler = (event: KeyboardEvent) => {
      if (event.key === "ArrowRight") {
        event.preventDefault();
        go(1);
      } else if (event.key === "ArrowLeft") {
        event.preventDefault();
        go(-1);
      }
    };

    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [go, open]);

  const active = index === null ? null : images[index];
  const activeNumber = index === null ? 0 : index + 1;

  return (
    <Dialog open={open} onOpenChange={(next) => (!next ? onClose() : undefined)}>
      <DialogContent
        showCloseButton={false}
        aria-describedby={undefined}
        className="flex h-[100dvh] max-h-none w-screen max-w-none flex-col gap-0 rounded-none border-0 bg-black/95 p-0 text-white sm:max-w-none"
      >
        <DialogTitle className="sr-only">
          {active?.title || `${name} images`}
        </DialogTitle>

        {active ? (
          <>
            <div className="flex items-center justify-between gap-4 px-4 py-3 sm:px-6">
              <span className="text-xs font-medium tracking-wide text-white/70">
                {activeNumber} / {total}
              </span>
              <button
                type="button"
                onClick={onClose}
                aria-label="Close image viewer"
                className="cursor-pointer rounded-full bg-white/10 p-2 transition-colors hover:bg-white/20"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="relative flex min-h-0 flex-1 items-center justify-center px-2 sm:px-16">
              {total > 1 ? (
                <>
                  <LightboxArrow
                    side="left"
                    onClick={() => go(-1)}
                    label="Previous image"
                  />
                  <LightboxArrow
                    side="right"
                    onClick={() => go(1)}
                    label="Next image"
                  />
                </>
              ) : null}

              <PropertyMedia
                src={active.image}
                name={active.title || name}
                variant="cover"
                className="max-h-full object-contain group-hover:scale-100"
              />
            </div>

            <div className="space-y-3 px-4 py-4 sm:px-6">
              {active.title ? (
                <p className="text-base font-semibold">{active.title}</p>
              ) : null}
              {active.description ? (
                <p className="max-w-3xl text-sm leading-relaxed text-white/75">
                  {active.description}
                </p>
              ) : null}

              {total > 1 ? (
                <div className="flex gap-2 overflow-x-auto pb-1">
                  {images.map((image, imageIndex) => (
                    <button
                      key={`${image.image}-${imageIndex}`}
                      type="button"
                      onClick={() => onIndexChange(imageIndex)}
                      aria-label={image.title || `Show image ${imageIndex + 1}`}
                      aria-current={imageIndex === index}
                      className={cn(
                        "h-12 w-16 shrink-0 cursor-pointer overflow-hidden rounded-md border-2 transition-opacity",
                        imageIndex === index
                          ? "border-white"
                          : "border-transparent opacity-60 hover:opacity-100",
                      )}
                    >
                      <PropertyMedia
                        src={image.image}
                        name={image.title || name}
                        variant="thumb"
                        className="group-hover:scale-100"
                      />
                    </button>
                  ))}
                </div>
              ) : null}
            </div>
          </>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}

interface LightboxArrowProps {
  side: "left" | "right";
  label: string;
  onClick: () => void;
}

function LightboxArrow({ side, label, onClick }: LightboxArrowProps) {
  const Icon = side === "left" ? ChevronLeft : ChevronRight;

  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={label}
      className={cn(
        "absolute top-1/2 z-10 -translate-y-1/2 cursor-pointer rounded-full bg-white/10 p-2 transition-colors hover:bg-white/20",
        side === "left" ? "left-2 sm:left-4" : "right-2 sm:right-4",
      )}
    >
      <Icon className="h-5 w-5" />
    </button>
  );
}
