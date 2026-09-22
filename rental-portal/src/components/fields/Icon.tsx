"use client";

import { cn } from "@/lib/utils";
import { icons } from "lucide-react";
import * as React from "react";

interface IconProps {
  value?: string;
  onChange?: (val: string) => void;
  onBlur?: () => void;
  className?: string;
  disabled?: boolean;
  required?: boolean;
  label?: string;
  iconName?: string;
  size?: number;
}

const ICON_NAMES = [
  "Activity",
  "AlertCircle",
  "AlertTriangle",
  "Archive",
  "ArrowDown",
  "ArrowLeft",
  "ArrowRight",
  "ArrowUp",
  "Bell",
  "BookOpen",
  "Calendar",
  "Camera",
  "Check",
  "CheckCircle",
  "ChevronDown",
  "ChevronLeft",
  "ChevronRight",
  "ChevronUp",
  "Circle",
  "Clock",
  "Code",
  "Copy",
  "Database",
  "Download",
  "Edit",
  "Eye",
  "File",
  "FileText",
  "Filter",
  "Folder",
  "GitBranch",
  "Globe",
  "Heart",
  "HelpCircle",
  "Home",
  "Image",
  "Info",
  "Link",
  "List",
  "Lock",
  "LogOut",
  "Mail",
  "MapPin",
  "Menu",
  "MessageSquare",
  "MoreVertical",
  "Pencil",
  "Plus",
  "Printer",
  "RefreshCw",
  "Repeat",
  "Search",
  "Send",
  "Settings",
  "Share",
  "Shield",
  "ShoppingCart",
  "Star",
  "Sun",
  "Table",
  "Tag",
  "Trash",
  "Twitter",
  "Upload",
  "User",
  "Users",
  "Video",
  "Volume2",
  "X",
  "XCircle",
  "ZoomIn",
];

export const Icon = ({
  value = "",
  onChange,
  onBlur,
  className = "",
  disabled = false,
  required = false,
  label,
  iconName = "Circle",
  size = 16,
}: IconProps) => {
  const [isOpen, setIsOpen] = React.useState(false);
  const [search, setSearch] = React.useState("");
  const IconComponent = icons[iconName as keyof typeof icons];

  const filteredIcons = ICON_NAMES.filter((name) =>
    name.toLowerCase().includes(search.toLowerCase()),
  );

  const handleSelect = (name: string) => {
    onChange?.(name);
    setIsOpen(false);
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
      <div className="relative">
        <button
          type="button"
          onClick={() => !disabled && setIsOpen(!isOpen)}
          disabled={disabled}
          className={cn(
            "flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-xs transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 items-center gap-2",
            className,
          )}
          onBlur={onBlur}
        >
          {IconComponent && (
            <IconComponent size={size} className="text-foreground" />
          )}
          <span className="text-muted-foreground">
            {value || "Select icon..."}
          </span>
        </button>
        {isOpen && (
          <div className="absolute z-50 mt-1 p-2 bg-popover border border-input rounded-md shadow-md w-64 max-h-64 overflow-y-auto">
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search icons..."
              className="w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm mb-2"
            />
            <div className="grid grid-cols-4 gap-1.5">
              {filteredIcons.map((name) => {
                const IconComp = icons[name as keyof typeof icons];
                return (
                  <button
                    key={name}
                    type="button"
                    onClick={() => handleSelect(name)}
                    className={cn(
                      "flex items-center justify-center p-2 rounded-md hover:bg-accent transition-colors",
                      value === name && "bg-accent",
                    )}
                  >
                    <IconComp size={24} />
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
