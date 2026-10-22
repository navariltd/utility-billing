/**
 * DocTypeList – generic list view for Frappe doctypes with filtering, sorting, and pagination.
 *
 * Key dependencies: uses @tanstack/react-table for rendering, frappe-react-sdk for API calls.
 * Sub-components from ./list/ handle DataTable, FilterBar, PaginationBar, and SortDropdown.
 */

"use client";

import { getCoreRowModel, useReactTable } from "@tanstack/react-table";
import { useFrappeGetCall, useFrappePostCall } from "frappe-react-sdk";
import { Loader2, Plus, RefreshCw } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useUser } from "@/contexts/user-context";
import { isPermissionError } from "./form/parse-error";
import { buildDocTypeListColumns } from "./buildDocTypeListColumns";
import { computePaginationPages } from "./computePaginationPages";
import { DataTable } from "./list/DataTable";
import { FilterBar } from "./list/FilterBar";
import { PaginationBar } from "./list/PaginationBar";
import { SortDropdown } from "./list/SortDropdown";
import { type AppListColumn, type FilterItem } from "./types";
import { QUICK_DATE_RANGES } from "./utils";
import { useDocTypeListSchema } from "./useDocTypeListSchema";

interface DocTypeListProps {
  doctype: string;
  title?: string;
  extraColumns?: AppListColumn[];
  onRowNavigate?: (name: string) => void;
}

export function DocTypeList({
  doctype,
  title,
  extraColumns = [],
  onRowNavigate,
}: DocTypeListProps) {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { user, isLoading: userLoading } = useUser();

  const [rows, setRows] = useState<any[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [pageSize, setPageSize] = useState(20);
  const [sortField, setSortField] = useState("modified");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");
  const [sortDropdownOpen, setSortDropdownOpen] = useState(false);
  const [filterDropdownOpen, setFilterDropdownOpen] = useState(false);
  const [selectedNames, setSelectedNames] = useState<Set<string>>(new Set());
  const [filterRows, setFilterRows] = useState<FilterItem[]>([]);
  const [showLikedOnly, setShowLikedOnly] = useState(false);

  const {
    schemaFields,
    isSubmittable,
    metaLoaded,
    error,
    activeFilters,
    setActiveFilters,
  } = useDocTypeListSchema(doctype);

  const currentPage = Number(searchParams.get("page") || "1");

  // Sync filters to URL
  useEffect(() => {
    if (!metaLoaded) return;
    const params = new URLSearchParams();
    params.set("page", String(currentPage));
    params.set("sort", sortField);
    params.set("order", sortOrder);
    params.set("ps", String(pageSize));
    Object.entries(activeFilters).forEach(([key, f]) => {
      if (f.value) params.set(key, f.value);
    });
    setSearchParams(params, { replace: true });
  }, [activeFilters, currentPage, sortField, sortOrder, pageSize, metaLoaded]);

  // Build frappe-style filters array
  const frappeFilters = useMemo(() => {
    const f: any[] = [];
    Object.entries(activeFilters).forEach(([key, af]) => {
      if (!af.value) return;
      let op = af.operator;
      let val: any = af.value;
      let filterDoctype = doctype;
      let fieldKey = key;

      if (key.includes(".")) {
        filterDoctype = key.split(".")[0];
        fieldKey = key.split(".")[1];
      }

      // Handle comma-separated name list for "in" operator
      if (fieldKey === "name" && typeof val === "string" && val.includes(",") && !val.includes("%")) {
        const names = val.split(",").map((s: string) => s.trim()).filter(Boolean);
        if (names.length > 1) { f.push([filterDoctype, "name", "in", names]); return; }
      }

      // Handle JSON array values from URL params
      if (typeof val === "string" && val.startsWith("[") && val.endsWith("]")) {
        try {
          const parsed = JSON.parse(val);
          if (Array.isArray(parsed)) {
            if (Array.isArray(parsed[0])) { parsed.forEach((inner: any) => f.push([filterDoctype, fieldKey, inner[0], inner[1]])); return; }
            if (parsed.length === 2) { f.push([filterDoctype, fieldKey, parsed[0], parsed[1]]); return; }
          }
        } catch { /* not valid JSON */ }
      }

      if (op === "like" && typeof val === "string" && !val.includes("%")) val = `%${val}%`;
      if (op === "__starts_with") { op = "like"; val = `${val}%`; }
      if (op === "__ends_with") { op = "like"; val = `%${val}`; }
      f.push([filterDoctype, fieldKey, op, val]);
    });

    if (showLikedOnly && user?.name) f.push([doctype, "_liked_by", "like", `%${user.name}%`]);
    return f;
  }, [activeFilters, doctype, showLikedOnly, user]);

  const { data: countData, mutate: refetchCount } = useFrappeGetCall(
    "frappe.desk.reportview.get_count",
    { doctype, filters: JSON.stringify(frappeFilters), fields: JSON.stringify([]), distinct: false },
    doctype && metaLoaded ? `dtl-cnt-${doctype}-${JSON.stringify(frappeFilters)}` : null,
  );

  const { call: fetchList, result: listResult, loading: listLoading } = useFrappePostCall("frappe.desk.reportview.get");

  const standardFilterFields = useMemo(
    () => schemaFields.filter((f: any) => f.in_standard_filter === 1 && f.fieldname !== "name" && !["Tab Break", "Section Break", "Column Break"].includes(f.fieldtype)),
    [schemaFields],
  );

  const filterableFields = useMemo(
    () => schemaFields.filter((f: any) => !["Tab Break", "Section Break", "Column Break", "Fold", "Page Break"].includes(f.fieldtype) && !f.hidden),
    [schemaFields],
  );

  // Fetch list data
  useEffect(() => {
    if (!metaLoaded || !schemaFields.length || typeof fetchList !== "function") return;
    const fields = new Set(schemaFields.filter((f: any) => f.in_list_view).map((f: any) => f.fieldname));
    fields.add("name"); fields.add("creation"); fields.add("modified"); fields.add("owner");
    fields.add("_user_tags"); fields.add("_comments"); fields.add("_assign"); fields.add("_liked_by"); fields.add("idx");
    if (isSubmittable) fields.add("docstatus");

    setIsLoading(true);
    fetchList({
      doctype,
      fields: Array.from(fields).map((f) => `\`tab${doctype}\`.\`${f}\``),
      filters: frappeFilters,
      order_by: `\`tab${doctype}\`.\`${sortField}\` ${sortOrder}`,
      start: (currentPage - 1) * pageSize,
      page_length: pageSize || 999999,
      view: "List",
      with_comment_count: 1,
    }).catch((err: any) => { if (isPermissionError(err)) navigate("/errors/forbidden", { replace: true }); });
  }, [metaLoaded, schemaFields, doctype, currentPage, pageSize, frappeFilters, sortField, sortOrder, isSubmittable, fetchList, navigate]);

  useEffect(() => {
    if (listResult?.message) {
      const { keys, values } = listResult.message;
      setRows(keys && Array.isArray(values) ? values.map((row: any[]) => keys.reduce((acc: any, key: string, i: number) => { acc[key] = row[i]; return acc; }, {})) : []);
    }
    setIsLoading(false);
  }, [listResult]);

  useEffect(() => { if (countData?.message !== undefined) setTotalCount(countData.message || 0); }, [countData]);

  useEffect(() => {
    if (totalCount === 0 && currentPage > 1 && metaLoaded) {
      const params = new URLSearchParams(searchParams);
      params.set("page", "1");
      setSearchParams(params, { replace: true });
    }
  }, [totalCount, currentPage, metaLoaded]);

  useEffect(() => { if (error) setIsLoading(false); }, [error]);

  // Toggle like handler
  const handleToggleLike = async (row: any) => {
    try {
      const res = await fetch("/api/method/frappe.desk.like.toggle_like", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ doctype, name: row.name, add: row._liked_by?.includes(user?.name || "") ? "No" : "Yes" }),
      });
      if (res.ok) { refetchCount(); /* list re-fetch will happen via effect */ }
    } catch { /* ignore */ }
  };

  // Column definitions
  const listColumns = useMemo(() => {
    const cols: AppListColumn[] = [{ fieldname: "name", label: "ID", fieldtype: "Data" }];
    schemaFields.filter((f: any) => f.in_list_view && f.fieldname !== "name").forEach((f: any) =>
      cols.push({ fieldname: f.fieldname, label: f.label || f.fieldname, fieldtype: f.fieldtype }),
    );
    if (isSubmittable) cols.push({ fieldname: "docstatus", label: "Status", fieldtype: "Select" });
    cols.push(...extraColumns);
    return cols;
  }, [schemaFields, isSubmittable, extraColumns]);

  const columnDefs = useMemo(() =>
    buildDocTypeListColumns({
      listColumns, rows, selectedNames, setSelectedNames,
      user: user ?? null, onToggleLike: handleToggleLike,
      showLikedOnly, setShowLikedOnly,
    }),
  [listColumns, selectedNames, rows, user, showLikedOnly]);

  const table = useReactTable({ data: rows, columns: columnDefs, getCoreRowModel: getCoreRowModel(), manualPagination: true });
  const totalPages = pageSize === 0 ? 1 : Math.max(1, Math.ceil(totalCount / pageSize));
  const paginationPages = useMemo(() => computePaginationPages(totalPages, currentPage), [totalPages, currentPage]);

  const handleFilterChange = (fn: string, op: string, v: string) =>
    setActiveFilters((p) => ({ ...p, [fn]: { ...(p[fn] || { operator: "like", fieldtype: "Data" }), operator: op, value: v } }));
  const removeFilter = (fn: string) => setActiveFilters((p) => { const n = { ...p }; delete n[fn]; return n; });
  const clearFilters = () => { setActiveFilters({ name: { value: "", operator: "like", fieldtype: "Data" } }); setFilterRows([]); };
  const applyFilters = () => {
    const newActive: Record<string, any> = {};
    filterRows.forEach((pf) => { if (pf.fieldname && pf.value) newActive[pf.fieldname] = { value: pf.value, operator: pf.operator, fieldtype: pf.fieldtype }; });
    if (Object.keys(newActive).length > 0) setActiveFilters((prev) => ({ ...prev, ...newActive }));
    setFilterRows([]);
  };

  useEffect(() => {
    if (filterDropdownOpen && filterRows.length === 0) {
      const rows: FilterItem[] = [];
      Object.entries(activeFilters).forEach(([key, af]) => {
        if (key === "name" || !af.value) return;
        rows.push({ fieldname: key, operator: af.operator, value: af.value, fieldtype: af.fieldtype });
      });
      if (rows.length > 0) setFilterRows(rows);
    }
  }, [filterDropdownOpen, activeFilters, filterRows.length]);

  const applyQuickDate = (range: typeof QUICK_DATE_RANGES[0]) => {
    const past = new Date(Date.now() - range.minutes * 60 * 1000).toISOString().slice(0, 19);
    setActiveFilters((p) => ({ ...p, modified: { value: past, operator: ">=", fieldtype: "Datetime" } }));
  };

  const rowClick = (name: string) => {
    if (onRowNavigate) onRowNavigate(name);
    else navigate(`/app/${doctype.toLowerCase().replace(/ /g, "-")}/${name}`);
  };
  const handleNew = () => {
    const params = new URLSearchParams();
    Object.entries(activeFilters).forEach(([key, af]) => {
      if (!af.value || key === "name") return;
      if (af.operator === "=" || af.operator === "like") params.set(key, af.value);
    });
    const qs = params.toString();
    navigate(`/app/${doctype.toLowerCase().replace(/ /g, "-")}/new${qs ? `?${qs}` : ""}`);
  };

  const sortableFields = schemaFields
    .filter((f: any) => f.sortable !== 0 && !["Tab Break", "Section Break", "Column Break"].includes(f.fieldtype))
    .map((f: any) => ({ value: f.fieldname, label: f.label || f.fieldname }));
  const hasActiveFilters = Object.keys(activeFilters).some((k) => k !== "name" && activeFilters[k].value !== "");

  if (userLoading) return <div className="flex items-center justify-center py-20"><Loader2 className="h-8 w-8 animate-spin text-muted-foreground" /></div>;

  return (
    <div className="px-4 lg:px-6 space-y-4 pb-8">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold tracking-tight">{title || doctype}</h1>
          {selectedNames.size > 0 && <Badge variant="secondary" className="text-xs">{selectedNames.size} selected</Badge>}
          <p className="text-muted-foreground text-sm">{totalCount} record{totalCount !== 1 ? "s" : ""}</p>
        </div>
        <div className="flex items-center gap-2">
          <SortDropdown open={sortDropdownOpen} onOpenChange={setSortDropdownOpen} fields={sortableFields}
            sortField={sortField} sortOrder={sortOrder} onSortFieldChange={setSortField} onSortOrderChange={setSortOrder} />
          <Button variant="outline" size="sm" className="h-8 text-xs gap-1" onClick={() => refetchCount()} disabled={isLoading || listLoading}>
            <RefreshCw className={`h-3.5 w-3.5 ${isLoading || listLoading ? "animate-spin" : ""}`} /> Refresh
          </Button>
          <Button size="sm" className="h-8 text-xs gap-1" onClick={handleNew}><Plus className="h-3.5 w-3.5" /> New</Button>
        </div>
      </div>

      {error && <div className="p-3 bg-destructive/10 border border-destructive/20 text-destructive rounded-md text-sm">{error}</div>}

      <FilterBar standardFilterFields={standardFilterFields} activeFilters={activeFilters}
        onFilterChange={handleFilterChange} onRemoveFilter={removeFilter} onClearFilters={clearFilters}
        filterDropdownOpen={filterDropdownOpen} onFilterDropdownOpenChange={setFilterDropdownOpen}
        filterRows={filterRows} onSetFilterRows={setFilterRows} filterableFields={filterableFields}
        onApplyFilters={applyFilters} schemaFields={schemaFields} />

      <DataTable table={table} columns={columnDefs.length} isLoading={isLoading || listLoading}
        hasActiveFilters={hasActiveFilters} title={title} doctype={doctype}
        selectedNames={selectedNames} onRowClick={rowClick} />

      <PaginationBar pageSize={pageSize} onPageSizeChange={setPageSize} currentPage={currentPage}
        totalPages={totalPages} totalCount={totalCount}
        onPageChange={(p) => setSearchParams((prev) => { const n = new URLSearchParams(prev); n.set("page", String(p)); return n; }, { replace: true })}
        onQuickDate={applyQuickDate} paginationPages={paginationPages} />
    </div>
  );
}

export default DocTypeList;