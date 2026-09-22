"use client";

import { cn } from "@/lib/utils";
import { Image as ImageIcon, Upload, X } from "lucide-react";
import * as React from "react";

interface ImageProps {
  value: string | File | null;
  onChange: (val: File | null) => void;
  onBlur?: () => void;
  className?: string;
  disabled?: boolean;
  required?: boolean;
  label?: string;
  accept?: string;
  maxSize?: number; // in bytes
}

export const Image = ({
  value = null,
  onChange,
  onBlur,
  className = "",
  disabled = false,
  required = false,
  label,
  accept = "image/*",
  maxSize = 5 * 1024 * 1024, // 5MB
}: ImageProps) => {
  const [preview, setPreview] = React.useState<string | null>(null);
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  React.useEffect(() => {
    if (value instanceof File) {
      const reader = new FileReader();
      reader.onloadend = () => {
        setPreview(reader.result as string);
      };
      reader.readAsDataURL(value);
    } else if (typeof value === "string") {
      setPreview(value);
    } else {
      setPreview(null);
    }
  }, [value]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (file.size > maxSize) {
        alert(`File size exceeds ${maxSize / 1024 / 1024}MB limit`);
        return;
      }
      onChange(file);
    }
  };

  const handleRemove = () => {
    onChange(null);
    setPreview(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
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
      <div className="flex items-start gap-4">
        {preview ? (
          <div className="relative">
            <img
              src={preview}
              alt="Preview"
              className="w-32 h-32 object-cover rounded-md border"
            />
            {!disabled && (
              <button
                type="button"
                onClick={handleRemove}
                className="absolute -top-2 -right-2 p-1 bg-destructive text-destructive-foreground rounded-full hover:bg-destructive/90 transition-colors"
              >
                <X className="size-3.5" />
              </button>
            )}
          </div>
        ) : (
          <div
            className={cn(
              "w-32 h-32 flex flex-col items-center justify-center border-2 border-dashed rounded-md bg-muted/20",
              disabled && "opacity-50 cursor-not-allowed",
            )}
          >
            <ImageIcon className="size-8 text-muted-foreground" />
            <span className="text-xs text-muted-foreground mt-1">No image</span>
          </div>
        )}
        <div className="flex-1">
          <input
            ref={fileInputRef}
            type="file"
            accept={accept}
            onChange={handleFileChange}
            onBlur={onBlur}
            disabled={disabled}
            className="hidden"
          />
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={disabled}
            className={cn(
              "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 border border-input bg-background shadow-sm hover:bg-accent hover:text-accent-foreground h-9 px-4 py-2",
              className,
            )}
          >
            <Upload className="size-4" />
            Upload Image
          </button>
          <p className="text-xs text-muted-foreground mt-2">
            Max size: {maxSize / 1024 / 1024}MB
          </p>
        </div>
      </div>
    </div>
  );
};
