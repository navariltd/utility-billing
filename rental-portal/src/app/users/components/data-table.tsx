"use client";

import {
  type ColumnDef,
  type ColumnFiltersState,
  type Row,
  type SortingState,
  type VisibilityState,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
} from "@tanstack/react-table";
import {
  ChevronDown,
  Download,
  EllipsisVertical,
  Eye,
  Search,
  Trash2,
  UserCheck,
  UserX,
} from "lucide-react";
import { useState } from "react";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { UserFormDialog } from "./user-form-dialog";

interface FrappeUser {
  name: string;
  [key: string]: any;
}

interface UserFormValues {
  [key: string]: any;
}

interface DataTableProps {
  users: FrappeUser[];
  onDeleteUser: (user: FrappeUser) => void;
  onEditUser: (user: FrappeUser, field: string, value: any) => void;
  onAddUser: (userData: UserFormValues) => void;
  onToggleStatus: (user: FrappeUser) => void;
  isLoading?: boolean;
  isSystemAdmin?: boolean;
  listFields?: string[];
  filterFields?: string[];
  standardFilterFields?: string[];
}

export function DataTable({
  users,
  onDeleteUser,
  onEditUser,
  onAddUser,
  onToggleStatus,
  isLoading,
  isSystemAdmin = false,
  listFields = [],
  filterFields = [],
  standardFilterFields = [],
}: DataTableProps) {
  const [sorting, setSorting] = useState<SortingState>([]);
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([]);
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({});
  const [rowSelection, setRowSelection] = useState({});
  const [globalFilter, setGlobalFilter] = useState("");

  const getStatusColor = (enabled: boolean) => {
    return enabled
      ? "text-green-600 bg-green-50 dark:text-green-400 dark:bg-green-900/20"
      : "text-gray-600 bg-gray-50 dark:text-gray-400 dark:bg-gray-900/20";
  };

  const getRoleColor = (userType: string) => {
    switch (userType) {
      case "System User":
        return "text-blue-600 bg-blue-50 dark:text-blue-400 dark:bg-blue-900/20";
      case "Website User":
        return "text-green-600 bg-green-50 dark:text-green-400 dark:bg-green-900/20";
      default:
        return "text-gray-600 bg-gray-50 dark:text-gray-400 dark:bg-gray-900/20";
    }
  };

  const exactFilter = (
    row: Row<FrappeUser>,
    columnId: string,
    value: string,
  ) => {
    return row.getValue(columnId) === value;
  };

  const getDisplayValue = (value: any) => {
    if (value === null || value === undefined) return "";
    if (typeof value === "boolean") return value ? "Yes" : "No";
    return String(value);
  };

  const capitalizeHeader = (field: string) => {
    return field
      .split("_")
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(" ");
  };

  const defaultColumns: ColumnDef<FrappeUser>[] = [
    {
      id: "select",
      header: ({ table }) => (
        <div className="flex items-center justify-center px-2">
          <Checkbox
            checked={
              table.getIsAllPageRowsSelected() ||
              (table.getIsSomePageRowsSelected() && "indeterminate")
            }
            onCheckedChange={(value) =>
              table.toggleAllPageRowsSelected(!!value)
            }
            aria-label="Select all"
          />
        </div>
      ),
      cell: ({ row }) => (
        <div className="flex items-center justify-center px-2">
          <Checkbox
            checked={row.getIsSelected()}
            onCheckedChange={(value) => row.toggleSelected(!!value)}
            aria-label="Select row"
          />
        </div>
      ),
      enableSorting: false,
      enableHiding: false,
      size: 50,
    },
    {
      accessorKey: "name",
      header: "Name",
      cell: ({ row }) => {
        const user = row.original;
        const displayName = user.full_name || user.username || user.name;
        return (
          <div className="flex items-center gap-3">
            <Avatar className="h-8 w-8">
              <AvatarFallback className="text-xs font-medium">
                {user.user_image ? (
                  <img
                    src={user.user_image}
                    alt={displayName}
                    className="h-full w-full object-cover"
                  />
                ) : displayName ? (
                  displayName[0].toUpperCase()
                ) : (
                  "U"
                )}
              </AvatarFallback>
            </Avatar>
            <div className="flex flex-col">
              <span className="font-medium">{displayName}</span>
              <span className="text-sm text-muted-foreground">
                {user.email || ""}
              </span>
            </div>
          </div>
        );
      },
    },
    {
      accessorKey: "enabled",
      header: "Status",
      cell: ({ row }) => {
        const enabled = row.getValue("enabled") as boolean;
        return (
          <Badge variant="secondary" className={getStatusColor(enabled)}>
            {enabled ? "Active" : "Inactive"}
          </Badge>
        );
      },
      filterFn: exactFilter,
    },
    {
      id: "actions",
      header: "Actions",
      cell: ({ row }) => {
        const user = row.original;
        return (
          <div className="flex items-center gap-2">
            {isSystemAdmin && user.name !== "Administrator" && (
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 cursor-pointer"
                onClick={() => onToggleStatus(user)}
              >
                {user.enabled ? (
                  <UserX className="size-4" />
                ) : (
                  <UserCheck className="size-4" />
                )}
                <span className="sr-only">
                  {user.enabled ? "Deactivate" : "Activate"} user
                </span>
              </Button>
            )}
            {isSystemAdmin && (
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 cursor-pointer"
              >
                <Eye className="size-4" />
                <span className="sr-only">View user</span>
              </Button>
            )}
            {isSystemAdmin && (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 cursor-pointer"
                  >
                    <EllipsisVertical className="size-4" />
                    <span className="sr-only">More actions</span>
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem className="cursor-pointer">
                    View Details
                  </DropdownMenuItem>
                  <DropdownMenuItem className="cursor-pointer">
                    Send Email
                  </DropdownMenuItem>
                  <DropdownMenuItem className="cursor-pointer">
                    Reset Password
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  {user.name !== "Administrator" && (
                    <DropdownMenuItem
                      variant="destructive"
                      className="cursor-pointer"
                      onClick={() => onDeleteUser(user)}
                    >
                      <Trash2 className="mr-2 size-4" />
                      Delete User
                    </DropdownMenuItem>
                  )}
                </DropdownMenuContent>
              </DropdownMenu>
            )}
          </div>
        );
      },
    },
  ];

  const dynamicColumns: ColumnDef<FrappeUser>[] = listFields
    .filter((field) => !["name", "enabled", "email"].includes(field))
    .map((field) => ({
      accessorKey: field,
      header: capitalizeHeader(field),
      cell: ({ row }) => {
        const value = row.getValue(field);
        return <span className="text-sm">{getDisplayValue(value)}</span>;
      },
    }));

  const allColumns = [...defaultColumns, ...dynamicColumns];

  const table = useReactTable({
    data: users,
    columns: allColumns,
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    getCoreRowModel: getCoreRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    onColumnVisibilityChange: setColumnVisibility,
    onRowSelectionChange: setRowSelection,
    onGlobalFilterChange: setGlobalFilter,
    state: {
      sorting,
      columnFilters,
      columnVisibility,
      rowSelection,
      globalFilter,
    },
  });

  const hasFilters = filterFields.length > 0 || standardFilterFields.length > 0;

  if (isLoading && users.length === 0) {
    return (
      <div className="w-full space-y-4">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex flex-1 items-center space-x-2">
            <Skeleton className="h-10 w-[300px]" />
          </div>
          <div className="flex items-center space-x-2">
            <Skeleton className="h-10 w-[100px]" />
            <Skeleton className="h-10 w-[140px]" />
          </div>
        </div>
        <div className="rounded-md border">
          <div className="p-8 text-center">
            <Skeleton className="h-[200px] w-full" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full space-y-4">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-1 items-center space-x-2">
          <div className="relative flex-1 max-w-sm">
            <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search users..."
              value={globalFilter ?? ""}
              onChange={(event) => setGlobalFilter(String(event.target.value))}
              className="pl-9"
            />
          </div>
        </div>
        <div className="flex items-center space-x-2">
          {isSystemAdmin && (
            <Button
              variant="outline"
              className="cursor-pointer"
              disabled={isLoading}
            >
              <Download className="mr-2 size-4" />
              Export
            </Button>
          )}
          <UserFormDialog
            onAddUser={onAddUser}
            isLoading={isLoading}
            isSystemAdmin={isSystemAdmin}
          />
        </div>
      </div>

      {hasFilters && (
        <div className="grid gap-2 sm:grid-cols-4 sm:gap-4">
          {standardFilterFields.map((field) => (
            <div key={field} className="space-y-2">
              <Label
                htmlFor={`${field}-filter`}
                className="text-sm font-medium"
              >
                {capitalizeHeader(field)}
              </Label>
              <Select
                value={
                  (table.getColumn(field)?.getFilterValue() as string) || ""
                }
                onValueChange={(value) =>
                  table
                    .getColumn(field)
                    ?.setFilterValue(value === "all" ? "" : value)
                }
              >
                <SelectTrigger
                  className="cursor-pointer w-full"
                  id={`${field}-filter`}
                >
                  <SelectValue
                    placeholder={`Select ${capitalizeHeader(field)}`}
                  />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All</SelectItem>
                  {Array.from(
                    new Set(
                      users
                        .map((u) => u[field])
                        .filter(
                          (v) => v !== null && v !== undefined && v !== "",
                        ),
                    ),
                  ).map((value) => (
                    <SelectItem key={String(value)} value={String(value)}>
                      {String(value)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          ))}
          {filterFields.map((field) => {
            if (standardFilterFields.includes(field)) return null;
            return (
              <div key={field} className="space-y-2">
                <Label
                  htmlFor={`${field}-filter`}
                  className="text-sm font-medium"
                >
                  {capitalizeHeader(field)}
                </Label>
                <Select
                  value={
                    (table.getColumn(field)?.getFilterValue() as string) || ""
                  }
                  onValueChange={(value) =>
                    table
                      .getColumn(field)
                      ?.setFilterValue(value === "all" ? "" : value)
                  }
                >
                  <SelectTrigger
                    className="cursor-pointer w-full"
                    id={`${field}-filter`}
                  >
                    <SelectValue
                      placeholder={`Select ${capitalizeHeader(field)}`}
                    />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All</SelectItem>
                    {Array.from(
                      new Set(
                        users
                          .map((u) => u[field])
                          .filter(
                            (v) => v !== null && v !== undefined && v !== "",
                          ),
                      ),
                    ).map((value) => (
                      <SelectItem key={String(value)} value={String(value)}>
                        {String(value)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            );
          })}
          <div className="space-y-2">
            <Label htmlFor="column-visibility" className="text-sm font-medium">
              Column Visibility
            </Label>
            <DropdownMenu>
              <DropdownMenuTrigger asChild id="column-visibility">
                <Button variant="outline" className="cursor-pointer w-full">
                  Columns <ChevronDown className="ml-2 size-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                {table
                  .getAllColumns()
                  .filter((column) => column.getCanHide())
                  .map((column) => {
                    return (
                      <DropdownMenuCheckboxItem
                        key={column.id}
                        className="capitalize"
                        checked={column.getIsVisible()}
                        onCheckedChange={(value) =>
                          column.toggleVisibility(!!value)
                        }
                      >
                        {column.id}
                      </DropdownMenuCheckboxItem>
                    );
                  })}
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      )}

      <div className="rounded-md border">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => {
                  return (
                    <TableHead key={header.id}>
                      {header.isPlaceholder
                        ? null
                        : flexRender(
                            header.column.columnDef.header,
                            header.getContext(),
                          )}
                    </TableHead>
                  );
                })}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {table.getRowModel().rows?.length ? (
              table.getRowModel().rows.map((row) => (
                <TableRow
                  key={row.id}
                  data-state={row.getIsSelected() && "selected"}
                >
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id}>
                      {flexRender(
                        cell.column.columnDef.cell,
                        cell.getContext(),
                      )}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell
                  colSpan={allColumns.length}
                  className="h-24 text-center"
                >
                  No results.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      <div className="flex items-center justify-between space-x-2 py-4">
        <div className="flex items-center space-x-2">
          <Label htmlFor="page-size" className="text-sm font-medium">
            Show
          </Label>
          <Select
            value={`${table.getState().pagination.pageSize}`}
            onValueChange={(value) => {
              table.setPageSize(Number(value));
            }}
          >
            <SelectTrigger className="w-20 cursor-pointer" id="page-size">
              <SelectValue placeholder={table.getState().pagination.pageSize} />
            </SelectTrigger>
            <SelectContent side="top">
              {[10, 20, 30, 40, 50].map((pageSize) => (
                <SelectItem key={pageSize} value={`${pageSize}`}>
                  {pageSize}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="flex-1 text-sm text-muted-foreground hidden sm:block">
          {table.getFilteredSelectedRowModel().rows.length} of{" "}
          {table.getFilteredRowModel().rows.length} row(s) selected.
        </div>
        <div className="flex items-center space-x-6 lg:space-x-8">
          <div className="flex items-center space-x-2 hidden sm:flex">
            <p className="text-sm font-medium">Page</p>
            <strong className="text-sm">
              {table.getState().pagination.pageIndex + 1} of{" "}
              {table.getPageCount()}
            </strong>
          </div>
          <div className="flex items-center space-x-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => table.previousPage()}
              disabled={!table.getCanPreviousPage()}
              className="cursor-pointer"
            >
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => table.nextPage()}
              disabled={!table.getCanNextPage()}
              className="cursor-pointer"
            >
              Next
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
