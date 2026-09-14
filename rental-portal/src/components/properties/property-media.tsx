/**
 * Property media – the property picture, or an initials placeholder when the
 * property has no image.
 */

"use client";

import { Building2 } from "lucide-react";
import { useState } from "react";

import { cn } from "@/lib/utils";

interface PropertyMediaProps {
  src?: string | null;
  /** Name used for the alt text and the placeholder initials. */
  name: string;
  /** `cover` fills a card header, `thumb` is the small square used in list rows. */
  variant?: "cover" | "thumb";
  className?: string;
}

/** Build up to two initials from a property name, e.g. "Pinnacle Tower - 1A" → "PT". */
export function getInitials(name: string): string {
  const words = name
    .split(/[\s\-_/]+/)
    .filter((word) => /[a-z0-9]/i.test(word))
    .slice(0, 2);

  if (words.length === 0) {
    return "?";
  }

  return words.map((word) => word.charAt(0)).join("").toUpperCase();
}

/** Fully rounded image that falls back to a placeholder when missing or broken. */
export function PropertyMedia({
  src,
  name,
  variant = "cover",
  className,
}: PropertyMediaProps) {
  const [failed, setFailed] = useState(false);
  const showImage = Boolean(src) && !failed;

  const placeholder = (
    <div
      className={cn(
        "text-primary flex h-full w-full flex-col items-center justify-center gap-1 bg-primary/10",
        className,
      )}
      aria-hidden={showImage}
    >
      {variant === "cover" ? (
        <>
          <span className="text-2xl font-semibold tracking-wide">
            {getInitials(name)}
          </span>
          <Building2 className="h-4 w-4 opacity-60" />
        </>
      ) : (
        <span className="text-xs font-semibold">{getInitials(name)}</span>
      )}
    </div>
  );

  if (!showImage) {
    return placeholder;
  }

  return (
    <img
      src={src ?? undefined}
      alt={name}
      loading="lazy"
      onError={() => setFailed(true)}
      className={cn(
        "h-full w-full object-cover transition-transform duration-300 group-hover:scale-[1.03]",
        className,
      )}
    />
  );
}
