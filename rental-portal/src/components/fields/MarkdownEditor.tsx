"use client";

import { cn } from "@/lib/utils";
import { Eye, Pencil } from "lucide-react";
import * as React from "react";

interface MarkdownEditorProps {
  value: string;
  onChange: (val: string) => void;
  onBlur?: () => void;
  placeholder?: string;
  className?: string;
  disabled?: boolean;
  required?: boolean;
  label?: string;
  rows?: number;
}

export const MarkdownEditor = ({
  value = "",
  onChange,
  onBlur,
  placeholder = "Enter markdown...",
  className = "",
  disabled = false,
  required = false,
  label,
  rows = 8,
}: MarkdownEditorProps) => {
  const [mode, setMode] = React.useState<"edit" | "preview">("edit");

  const renderMarkdown = (text: string) => {
    // Simple markdown rendering (you can use a library like marked)
    return text
      .replace(/^# (.*$)/gim, "<h1>$1</h1>")
      .replace(/^## (.*$)/gim, "<h2>$1</h2>")
      .replace(/^### (.*$)/gim, "<h3>$1</h3>")
      .replace(/\*\*(.*)\*\*/gim, "<strong>$1</strong>")
      .replace(/\*(.*)\*/gim, "<em>$1</em>")
      .replace(/`(.*)`/gim, "<code>$1</code>")
      .replace(/\n/gim, "<br />");
  };

  return (
    <div className={cn("w-full flex flex-col gap-1.5", className)}>
      {label && (
        <div className="flex items-center justify-between">
          <label className="text-sm font-medium text-foreground flex items-center gap-0.5 select-none">
            {label}
            {required && (
              <span className="text-destructive font-bold text-red-500 ml-0.5">
                *
              </span>
            )}
          </label>
          <div className="flex gap-1">
            <button
              type="button"
              onClick={() => setMode("edit")}
              className={cn(
                "p-1 rounded-md text-xs transition-colors",
                mode === "edit"
                  ? "bg-primary text-primary-foreground"
                  : "hover:bg-muted",
              )}
              disabled={disabled}
            >
              <Pencil className="size-3.5" />
            </button>
            <button
              type="button"
              onClick={() => setMode("preview")}
              className={cn(
                "p-1 rounded-md text-xs transition-colors",
                mode === "preview"
                  ? "bg-primary text-primary-foreground"
                  : "hover:bg-muted",
              )}
              disabled={disabled}
            >
              <Eye className="size-3.5" />
            </button>
          </div>
        </div>
      )}
      {mode === "edit" ? (
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onBlur={onBlur}
          disabled={disabled}
          placeholder={placeholder}
          rows={rows}
          className={cn(
            "font-mono text-sm w-full rounded-md border border-input bg-background px-3 py-2 shadow-xs transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50",
            className,
          )}
        />
      ) : (
        <div
          className="w-full rounded-md border border-input bg-background px-3 py-2 min-h-[200px] prose prose-sm max-w-none"
          dangerouslySetInnerHTML={{ __html: renderMarkdown(value) }}
        />
      )}
    </div>
  );
};
