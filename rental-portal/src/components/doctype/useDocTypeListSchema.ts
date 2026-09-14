/**
 * useDocTypeListSchema – loads Frappe doctype schema, builds child table field maps, and initializes filters.
 *
 * Key dependencies: frappe-react-sdk useFrappeGetCall, used by DocTypeList component.
 */

import { useCallback, useEffect, useState } from "react";
import { useLocation, useSearchParams } from "react-router-dom";
import { useFrappeGetCall } from "frappe-react-sdk";

import type { ActiveFilter } from "./types";

interface UseDocTypeListSchemaResult {
  /** Raw schema fields from the doctype definition. */
  schemaFields: any[];
  /** Map of child table fields: { fieldname: { doctype, fieldname } }. */
  childTableFields: Record<string, { doctype: string; fieldname: string }>;
  /** Whether the doctype supports submission. */
  isSubmittable: boolean;
  /** Whether metadata has been fully loaded. */
  metaLoaded: boolean;
  /** Error message if schema loading failed. */
  error: string | null;
  /** Current active filters derived from route options. */
  activeFilters: Record<string, ActiveFilter>;
  /** Setter for active filters. */
  setActiveFilters: React.Dispatch<React.SetStateAction<Record<string, ActiveFilter>>>;
}

/**
 * Hook that loads doctype metadata and initializes filters from route options.
 *
 * Args:
 *   doctype: The Frappe doctype name.
 *
 * Returns:
 *   Schema state including fields, child table map, filters, and loading status.
 */
export function useDocTypeListSchema(doctype: string): UseDocTypeListSchemaResult {
  const location = useLocation();
  const [searchParams] = useSearchParams();

  const [schemaFields, setSchemaFields] = useState<any[]>([]);
  const [childTableFields, setChildTableFields] = useState<Record<string, { doctype: string; fieldname: string }>>({});
  const [isSubmittable, setIsSubmittable] = useState(false);
  const [metaLoaded, setMetaLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeFilters, setActiveFilters] = useState<Record<string, ActiveFilter>>({});

  const { data: schemaData, error: schemaError } = useFrappeGetCall(
    "frappe.desk.form.load.getdoctype",
    { doctype },
    doctype ? `dtl-meta-${doctype}` : null,
  );

  /** Build a lookup of child table fields from schema. */
  const buildChildTableFieldMap = useCallback(
    (metaFields: any[], allDocs: any[]) => {
      const map: Record<string, { doctype: string; fieldname: string }> = {};
      if (!metaFields) return map;

      const childTableDocTypes: string[] = [];
      metaFields.forEach((f: any) => {
        if (f.fieldtype === "Table") {
          childTableDocTypes.push(f.options);
        }
      });

      if (childTableDocTypes.length > 0) {
        allDocs.forEach((doc: any) => {
          if (childTableDocTypes.includes(doc.name) && doc.fields) {
            doc.fields.forEach((childField: any) => {
              if (!map[childField.fieldname]) {
                map[childField.fieldname] = {
                  doctype: doc.name,
                  fieldname: childField.fieldname,
                };
              }
            });
          }
        });
      }
      return map;
    },
    [],
  );

  useEffect(() => {
    if (schemaError) {
      setError("Failed to load schema");
      setMetaLoaded(true);
      return;
    }
    if (schemaData?.message?.docs?.length || schemaData?.docs?.length) {
      const docs = schemaData.message?.docs ?? schemaData.docs ?? [];
      const meta = docs.find((d: any) => d.name === doctype) ?? docs[0];
      if (meta) {
        const fields = meta.fields ?? [];
        setSchemaFields(fields);
        setIsSubmittable(meta.is_submittable === 1);

        const cfMap = buildChildTableFieldMap(fields, docs);
        setChildTableFields(cfMap);

        const isValidField = (fieldname: string): boolean => {
          if (["name", "docstatus", "owner", "creation", "modified", "modified_by",
               "_user_tags", "_comments", "_assign", "_liked_by", "idx"].includes(fieldname))
            return true;
          if (fields.some((f: any) => f.fieldname === fieldname)) return true;
          if (cfMap[fieldname]) return true;
          return false;
        };

        const getFilterKey = (fieldname: string): string | null => {
          if (fieldname.includes(".")) return fieldname;
          if (fields.some((f: any) => f.fieldname === fieldname)) return fieldname;
          if (cfMap[fieldname]) return `${cfMap[fieldname].doctype}.${fieldname}`;
          return null;
        };

        const initial: Record<string, ActiveFilter> = {};
        const allRouteOpts: Record<string, string> = {};

        const stateRouteOptions = (location.state as any)?.routeOptions;
        if (stateRouteOptions && typeof stateRouteOptions === "object") {
          for (const [key, value] of Object.entries(stateRouteOptions)) {
            allRouteOpts[key] = String(value ?? "");
          }
        }

        for (const [key, val] of searchParams.entries()) {
          allRouteOpts[key] = val;
        }

        for (const [key, val] of Object.entries(allRouteOpts)) {
          if (["page", "sort", "order", "ps"].includes(key)) continue;
          const fieldPart = key.includes(".") ? key.split(".")[1] : key;
          if (!isValidField(fieldPart)) continue;

          const filterKey = getFilterKey(fieldPart);
          if (!filterKey) continue;

          if (filterKey === "name" || (filterKey.includes(".") && fieldPart === "name")) {
            initial[filterKey] = { value: val, operator: "like", fieldtype: "Data" };
          } else if (fieldPart === "docstatus") {
            initial.docstatus = { value: val, operator: "=", fieldtype: "Select" };
          } else {
            const fc = fields.find((f: any) => f.fieldname === fieldPart);
            initial[filterKey] = {
              value: val,
              operator: fc?.fieldtype === "Select" || fc?.fieldtype === "Link" ? "=" : "like",
              fieldtype: fc?.fieldtype || "Data",
            };
          }
        }

        if (!initial.name && !Object.keys(initial).some((k) => k === "name" || (k.includes(".") && k.endsWith(".name")))) {
          initial.name = { value: "", operator: "like", fieldtype: "Data" };
        }
        setActiveFilters(initial);
      }
      setMetaLoaded(true);
    }
  }, [schemaData, schemaError, doctype, location.state, buildChildTableFieldMap]);

  return {
    schemaFields,
    childTableFields,
    isSubmittable,
    metaLoaded,
    error,
    activeFilters,
    setActiveFilters,
  };
}