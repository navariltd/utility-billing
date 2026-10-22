/**
 * Small generic table used to render the documents related to a property.
 */

"use client";

import { Card, CardContent } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { FileText } from "lucide-react";
import type { ReactNode } from "react";

export interface DocumentColumn<T> {
  label: string;
  render: (row: T) => ReactNode;
  align?: "right";
}

export function formatDate(value?: string | null): string {
  if (!value) return "—";

  return new Date(value).toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

/** Map a Frappe `docstatus` value to its label. */
export function formatDocstatus(docstatus: number): string {
  return ["Draft", "Submitted", "Cancelled"][docstatus] ?? "—";
}

interface DocumentTableProps<T> {
  rows: T[];
  columns: DocumentColumn<T>[];
  emptyMessage: string;
}

export function DocumentTable<T extends { name: string }>({
  rows,
  columns,
  emptyMessage,
}: DocumentTableProps<T>) {
  if (rows.length === 0) {
    return (
      <Card>
        <CardContent className="text-muted-foreground flex flex-col items-center gap-2 py-10 text-sm">
          <FileText className="h-6 w-6" />
          {emptyMessage}
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="gap-0 overflow-hidden py-0">
      <CardContent className="p-0">
        <Table>
          <TableHeader>
            <TableRow>
              {columns.map((column) => (
                <TableHead
                  key={column.label}
                  className={column.align === "right" ? "text-right" : undefined}
                >
                  {column.label}
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((row) => (
              <TableRow key={row.name}>
                {columns.map((column) => (
                  <TableCell
                    key={`${row.name}-${column.label}`}
                    className={column.align === "right" ? "text-right" : undefined}
                  >
                    {column.render(row)}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
