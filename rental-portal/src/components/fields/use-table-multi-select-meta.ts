/**
 * useTableMultiSelectMeta – loads doctype metadata for TableMultiSelect to find the first Link field.
 *
 * Key dependencies: uses useCallPost from frappe-service to fetch doctype schema.
 */

import { useEffect, useRef, useState } from "react";

import { useCallPost } from "@/lib/frappe-service";

interface UseTableMultiSelectMetaResult {
  /** Fetched metadata object from Frappe. */
  docMeta: any;
  /** The first Link field doctype found in the schema. */
  linkDoctype: string;
  /** Whether metadata has been loaded. */
  hasLoadedMeta: boolean;
  /** Whether metadata is currently loading. */
  metaLoading: boolean;
  /** Error message if metadata loading failed. */
  errorMessage: string;
  /** The previous filters ref, used to detect filter changes. */
  prevFiltersRef: React.MutableRefObject<any>;
  /** External filters object. */
  filters: Record<string, any>;
}

/**
 * Hook to load doctype metadata for the TableMultiSelect component.
 *
 * Args:
 *   doctype: The source doctype.
 *   linkFieldname: Optional specific Link field fieldname to use.
 *   filters: Optional filters to track for changes.
 *
 * Returns:
 *   Metadata state including linkDoctype, loading status, and error messages.
 */
export function useTableMultiSelectMeta(
  doctype: string,
  linkFieldname?: string,
  filters: Record<string, any> = {},
): UseTableMultiSelectMetaResult {
  const [docMeta, setDocMeta] = useState<any>(null);
  const [hasLoadedMeta, setHasLoadedMeta] = useState(false);
  const [metaLoading, setMetaLoading] = useState(false);
  const [linkDoctype, setLinkDoctype] = useState<string>("");
  const [errorMessage, setErrorMessage] = useState<string>("");
  const prevFiltersRef = useRef(filters);

  const { post: fetchDocType } = useCallPost("frappe.desk.form.load.getdoctype");

  useEffect(() => {
    if (JSON.stringify(prevFiltersRef.current) !== JSON.stringify(filters)) {
      prevFiltersRef.current = filters;
    }
  }, [filters]);

  useEffect(() => {
    const loadMeta = async () => {
      if (!doctype || hasLoadedMeta) return;

      try {
        setMetaLoading(true);
        setErrorMessage("");

        const response = await fetchDocType({
          doctype: doctype,
          with_parent: 0,
        });

        if (response && (response as any).docs && (response as any).docs[0]) {
          const meta = (response as any).docs[0];
          setDocMeta(meta);

          const fields: any[] = meta.fields || [];
          let linkField: any = null;

          if (linkFieldname) {
            linkField = fields.find(
              (f: any) => f.fieldname === linkFieldname && f.fieldtype === "Link",
            );
          }

          if (!linkField) {
            linkField = fields.find((f: any) => f.fieldtype === "Link" && f.reqd === 1);
          }

          if (!linkField) {
            linkField = fields.find((f: any) => f.fieldtype === "Link");
          }

          if (linkField) {
            setLinkDoctype(linkField.options || "");
          } else {
            setLinkDoctype("");
            setErrorMessage(
              `"${doctype}" has no Link field. TableMultiSelect requires at least one Link field to work.`,
            );
          }
        }
        setHasLoadedMeta(true);
      } catch (error) {
        setErrorMessage("Failed to load doctype metadata.");
      } finally {
        setMetaLoading(false);
      }
    };

    loadMeta();
  }, [doctype, hasLoadedMeta, linkFieldname, fetchDocType]);

  return {
    docMeta,
    linkDoctype,
    hasLoadedMeta,
    metaLoading,
    errorMessage,
    prevFiltersRef,
    filters,
  };
}