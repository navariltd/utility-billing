/**
 * DataTable – table component with sticky left checkbox column and sticky right action group.
 *
 * Key dependencies: @tanstack/react-table for rendering, shadcn/ui Card/Table for layout.
 * The right sticky group (modified time, comments, likes) is pinned at a fixed width.
 */

import { type Table as TanTable, flexRender } from "@tanstack/react-table";

import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn } from "@/lib/utils";

const RIGHT_IDS = ["_modified", "_comments", "_liked"];
const STICKY_W = 120;

interface DataTableProps {
  table: TanTable<any>;
  columns: number;
  isLoading: boolean;
  hasActiveFilters: boolean;
  title?: string;
  doctype: string;
  selectedNames: Set<string>;
  onRowClick: (name: string) => void;
}

export function DataTable({
  table,
  columns,
  isLoading,
  hasActiveFilters,
  title,
  doctype,
  selectedNames,
  onRowClick,
}: DataTableProps) {
  const totalCols = table.getHeaderGroups()[0]?.headers.length || columns;
  const rows = table.getRowModel().rows;
  const isSticky = (id: string) => RIGHT_IDS.includes(id);

  return (
    <Card className="border rounded-lg overflow-hidden">
      <CardContent className="p-0 relative">
        <div className="absolute top-0 right-[120px] h-full w-px bg-border z-20 pointer-events-none" />
        <div className="overflow-x-auto">
          <Table className="border-collapse">
            <TableHeader>
              {table.getHeaderGroups().map((hg) => (
                <TableRow key={hg.id} className="border-b">
                  {hg.headers.map((h) =>
                    isSticky(h.id) ? null : (
                      <TableHead
                        key={h.id}
                        style={{ width: h.getSize(), minWidth: h.getSize() }}
                        className={cn(
                          "h-10 px-3 text-xs font-semibold uppercase tracking-wider bg-background whitespace-nowrap",
                          h.id === "_select" &&
                            "sticky left-0 z-10 shadow-[2px_0_4px_-2px_rgba(0,0,0,0.1)]",
                        )}
                      >
                        {flexRender(h.column.columnDef.header, h.getContext())}
                      </TableHead>
                    ),
                  )}
                  {hg.headers.some((h) => isSticky(h.id)) && (
                    <TableHead
                      style={{ width: STICKY_W, minWidth: STICKY_W }}
                      className="h-10 px-3 text-xs font-semibold uppercase tracking-wider bg-background whitespace-nowrap sticky right-0 z-10"
                    >
                      <div className="flex items-center gap-0">
                        {hg.headers
                          .filter((h) => isSticky(h.id))
                          .map((h) => (
                            <div
                              key={h.id}
                              style={{
                                width: h.getSize(),
                                minWidth: h.getSize(),
                              }}
                              className="flex items-center justify-center"
                            >
                              {flexRender(
                                h.column.columnDef.header,
                                h.getContext(),
                              )}
                            </div>
                          ))}
                      </div>
                    </TableHead>
                  )}
                </TableRow>
              ))}
            </TableHeader>
            <TableBody>
              {isLoading ? (
                <>
                  {Array.from({ length: 5 }).map((_, i) => (
                    <TableRow key={i}>
                      <TableCell className="px-3 py-2.5 bg-background sticky left-0 z-10">
                        <div className="flex items-center gap-3">
                          <Skeleton className="h-4 w-4 rounded" />
                          <Skeleton className="h-4 w-32" />
                        </div>
                      </TableCell>
                      {Array.from({ length: Math.min(totalCols - 1, 4) }).map(
                        (_, j) => (
                          <TableCell key={j} className="px-3 py-2.5">
                            <Skeleton
                              className="h-4"
                              style={{
                                width: `${[60, 80, 100, 70][j % 4]}px`,
                              }}
                            />
                          </TableCell>
                        ),
                      )}
                      <TableCell className="px-3 py-2.5 sticky right-0 z-10 bg-background">
                        <div className="flex items-center justify-center gap-1">
                          <Skeleton className="h-4 w-4 rounded" />
                          <Skeleton className="h-4 w-4 rounded" />
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </>
              ) : rows.length === 0 ? (
                <TableRow>
                  <TableCell
                    colSpan={totalCols + 1}
                    className="text-center py-16 bg-background"
                  >
                    <p className="text-muted-foreground">
                      {hasActiveFilters
                        ? `No ${title || doctype} found.`
                        : `No ${title || doctype || "records"} found.`}
                    </p>
                  </TableCell>
                </TableRow>
              ) : (
                rows.map((row) => {
                  const sc = row
                    .getVisibleCells()
                    .filter((c) => isSticky(c.column.id));
                  return (
                    <TableRow
                      key={row.original.name}
                      className={cn(
                        "border-b last:border-0 transition-colors",
                        selectedNames.has(row.original.name)
                          ? "bg-muted/50"
                          : "hover:bg-muted/30",
                      )}
                    >
                      {row.getVisibleCells().map((cell) =>
                        isSticky(cell.column.id) ? null : (
                          <TableCell
                            key={cell.id}
                            className={cn(
                              "px-3 py-2.5 whitespace-nowrap",
                              cell.column.id === "_select" &&
                                "sticky left-0 z-10 bg-background cursor-pointer",
                              cell.column.id !== "_select" && "cursor-pointer",
                            )}
                            onClick={() => {
                              if (cell.column.id !== "_select")
                                onRowClick(row.original.name);
                            }}
                          >
                            {flexRender(
                              cell.column.columnDef.cell,
                              cell.getContext(),
                            )}
                          </TableCell>
                        ),
                      )}
                      {sc.length > 0 && (
                        <TableCell className="px-3 py-2.5 whitespace-nowrap sticky right-0 z-10 bg-background">
                          <div className="flex items-center gap-0">
                            {sc.map((cell) => (
                              <div
                                key={cell.id}
                                style={{
                                  width: cell.column.getSize(),
                                  minWidth: cell.column.getSize(),
                                }}
                                className="flex items-center justify-center"
                              >
                                {flexRender(
                                  cell.column.columnDef.cell,
                                  cell.getContext(),
                                )}
                              </div>
                            ))}
                          </div>
                        </TableCell>
                      )}
                    </TableRow>
                  );
                })
              )}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
}
