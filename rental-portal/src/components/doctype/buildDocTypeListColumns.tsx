/**
 * buildDocTypeListColumns – creates the column definitions for the DocTypeList data table.
 *
 * Key dependencies: @tanstack/react-table ColumnDef, shadcn Badge/Checkbox.
 * Generates columns for select checkbox, data fields, docstatus badge, modified time, comments, and likes.
 */

import { ArrowUpDown, Clock } from "lucide-react";
import type { ColumnDef } from "@tanstack/react-table";

import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { cn } from "@/lib/utils";
import { DOCSTATUS_MAP, type AppListColumn } from "./types";
import { formatCellValue, timeAgo } from "./utils";

/** Liked button heart icon SVG path. */
const HEART_PATH = "M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z";

interface BuildColumnsParams {
  listColumns: AppListColumn[];
  rows: any[];
  selectedNames: Set<string>;
  setSelectedNames: React.Dispatch<React.SetStateAction<Set<string>>>;
  user: { name?: string } | null;
  onToggleLike?: (row: any) => void;
  showLikedOnly: boolean;
  setShowLikedOnly: React.Dispatch<React.SetStateAction<boolean>>;
}

/**
 * Build @tanstack/react-table column definitions for a doctype list.
 *
 * Args:
 *   params: Configuration including listColumns, selection state, and user info.
 *
 * Returns:
 *   Array of ColumnDef for use with useReactTable.
 */
export function buildDocTypeListColumns(params: BuildColumnsParams): ColumnDef<any>[] {
  const { listColumns, rows, selectedNames, setSelectedNames, user, onToggleLike, showLikedOnly, setShowLikedOnly } = params;

  const defs: ColumnDef<any>[] = [
    {
      id: "_select",
      header: () => (
        <Checkbox
          checked={rows.length > 0 && rows.every((r) => selectedNames.has(r.name))}
          onCheckedChange={() =>
            setSelectedNames(selectedNames.size === rows.length ? new Set() : new Set(rows.map((r) => r.name)))
          }
        />
      ),
      cell: ({ row }) => (
        <Checkbox
          checked={selectedNames.has(row.original.name)}
          onCheckedChange={() => {
            setSelectedNames((prev) => {
              const n = new Set(prev);
              if (n.has(row.original.name)) n.delete(row.original.name);
              else n.add(row.original.name);
              return n;
            });
          }}
        />
      ),
      size: 40,
      enableResizing: false,
    },
  ];

  listColumns.forEach((col) =>
    defs.push({
      id: col.fieldname,
      header: () => (
        <div className="flex items-center gap-1.5">
          <span>{col.label}</span>
          <ArrowUpDown className="h-3 w-3 text-muted-foreground/40" />
        </div>
      ),
      accessorKey: col.fieldname,
      cell: ({ getValue }) => {
        const val: any = getValue();
        if (col.fieldname === "docstatus") {
          const s = DOCSTATUS_MAP[val] ?? { label: String(val), variant: "outline" as const };
          return <Badge variant={s.variant as any}>{s.label}</Badge>;
        }
        return (
          <span className={cn("text-sm", col.fieldname === "name" && "font-medium")}>
            {formatCellValue(val, col.fieldtype)}
          </span>
        );
      },
      size: col.width,
    }),
  );

  defs.push({
    id: "_modified",
    header: () => null,
    accessorKey: "modified",
    cell: ({ getValue }) => (
      <div className="flex items-center justify-center" title={new Date(getValue() as string).toLocaleString()}>
        <Clock className="!ml-6 h-3 w-3 text-muted-foreground/60" />
        <span className="text-[10px] text-muted-foreground ml-0.5 tabular-nums">{timeAgo(getValue() as string)}</span>
      </div>
    ),
    size: 56,
    enableResizing: false,
  });

  defs.push({
    id: "_comments",
    header: () => null,
    accessorKey: "_comment_count",
    cell: ({ row }) => {
      const c = (row.original as any)._comment_count;
      const n = typeof c === "number" ? c : parseInt(c, 10) || 0;
      return (
        <div className="flex items-center justify-center gap-0.5" title={`${n} comment${n !== 1 ? "s" : ""}`}>
          <svg className="h-3 w-3 text-muted-foreground/60" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
          </svg>
          <span className="text-[10px] text-muted-foreground tabular-nums">{n}</span>
        </div>
      );
    },
    size: 36,
    enableResizing: false,
  });

  defs.push({
    id: "_liked",
    header: () => (
      <button
        type="button"
        onClick={() => setShowLikedOnly((p) => !p)}
        className={cn(
          "flex items-center justify-center w-full h-full cursor-pointer transition-colors rounded-sm",
          showLikedOnly ? "text-red-500" : "text-muted-foreground/40 hover:text-red-400",
        )}
        title={showLikedOnly ? "Show all" : "Show liked only"}
      >
        <svg className={cn("h-3.5 w-3.5", showLikedOnly ? "fill-current" : "")} viewBox="0 0 24 24" fill={showLikedOnly ? "currentColor" : "none"} stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d={HEART_PATH} />
        </svg>
      </button>
    ),
    accessorKey: "_liked_by",
    cell: ({ row }) => {
      const lb = (row.original as any)._liked_by;
      const liked = lb && typeof lb === "string" && lb.includes(user?.name || "");
      return (
        <div className="flex items-center justify-center">
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onToggleLike?.(row.original);
            }}
            className={cn(
              "cursor-pointer transition-colors p-0.5 rounded hover:bg-muted",
              liked ? "text-red-500 hover:text-red-600" : "text-muted-foreground/40 hover:text-red-400",
            )}
            title={liked ? "Unlike" : "Like"}
          >
            <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill={liked ? "currentColor" : "none"} stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d={HEART_PATH} />
            </svg>
          </button>
        </div>
      );
    },
    size: 36,
    enableResizing: false,
  });

  return defs;
}