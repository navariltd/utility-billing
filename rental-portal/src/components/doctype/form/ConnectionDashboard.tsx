/**
 * ConnectionDashboard – renders related-document link cards for a given doctype/docname.
 *
 * Fetches open-count data from Frappe and displays grouped transaction links with
 * counts and quick-create buttons.
 */

"use client";

import { useFrappeGetCall } from "frappe-react-sdk";
import { Plus } from "lucide-react";
import { useNavigate } from "react-router-dom";

interface ConnectionDashboardProps {
  doctype: string;
  docname?: string;
  metaConfig?: any;
}

function toSlug(dt: string): string {
  return dt.toLowerCase().replace(/ /g, "-");
}

/** Build route_options for navigation: keeps dot-notation for list filters, plain fieldname for new-doc prefills. */
function buildRouteOptions(
  docname: string | undefined,
  fieldname: string,
  nonStandardFieldnames: Record<string, string>,
  dynamicLinks: Record<string, [string, string]>,
  targetDoctype: string,
  isNew: boolean,
): Record<string, string> {
  const opts: Record<string, string> = {};
  if (!docname) return opts;

  const linkField = nonStandardFieldnames[targetDoctype] || fieldname;

  if (dynamicLinks && dynamicLinks[linkField]) {
    const [refDoctypeValue, refDoctypeField] = dynamicLinks[linkField];
    opts[linkField] = docname;
    opts[refDoctypeField] = refDoctypeValue;
  } else if (isNew || !linkField.includes(".")) {
    const cleanField = linkField.includes(".") ? linkField.split(".")[1] : linkField;
    opts[cleanField] = docname;
  } else {
    opts[linkField] = docname;
  }
  return opts;
}

/** Build an object with dashboard metadata extracted from metaConfig. */
function extractDashboardMeta(metaConfig: any) {
  const dashboard = metaConfig?.__dashboard || {};
  return {
    fieldname: dashboard.fieldname || "customer",
    nonStandardFieldnames: dashboard.non_standard_fieldnames || {},
    transactions: dashboard.transactions || [],
    internalLinks: dashboard.internal_links || {},
    dynamicLinks: dashboard.dynamic_links || {},
  };
}

export function ConnectionDashboard({
  doctype,
  docname,
  metaConfig,
}: ConnectionDashboardProps) {
  const navigate = useNavigate();
  const {
    fieldname,
    nonStandardFieldnames,
    transactions,
    internalLinks,
    dynamicLinks,
  } = extractDashboardMeta(metaConfig);

  const trackableItems = transactions.reduce((acc: string[], group: any) => {
    if (group?.items) acc.push(...group.items);
    return acc;
  }, []);

  const hasDoc = !!(doctype && docname && trackableItems.length > 0);

  const { data: notificationData } = useFrappeGetCall(
    "frappe.desk.notifications.get_open_count",
    hasDoc
      ? { doctype, name: docname!, items: trackableItems }
      : undefined,
    hasDoc
      ? (`conn-dash-${doctype}-${docname!}-${trackableItems.join(",")}` as string)
      : undefined,
  );

  const countData = notificationData?.message?.count || {};
  const externalLinks: any[] = countData?.external_links_found || [];
  const internalLinksFound: any[] = countData?.internal_links_found || [];
  const combinedLinks = [...externalLinks, ...internalLinksFound];

  if (combinedLinks.length === 0) return null;

  const linkMap = new Map(combinedLinks.map((link: any) => [link.doctype, link]));

  const handleNavigateToList = (targetDoctype: string) => {
    const slug = toSlug(targetDoctype);
    const matched = linkMap.get(targetDoctype);

    if (matched?.names && matched.names.length > 0) {
      navigate(`/app/${slug}`, {
        state: { routeOptions: { name: matched.names.join(",") } },
      });
      return;
    }

    navigate(`/app/${slug}`, {
      state: {
        routeOptions: buildRouteOptions(
          docname, fieldname, nonStandardFieldnames, dynamicLinks, targetDoctype, false,
        ),
      },
    });
  };

  const handleNavigateToNew = (targetDoctype: string) => {
    const slug = toSlug(targetDoctype);
    navigate(`/app/${slug}/new`, {
      state: {
        routeOptions: buildRouteOptions(
          docname, fieldname, nonStandardFieldnames, dynamicLinks, targetDoctype, true,
        ),
      },
    });
  };

  const activeSections = transactions.filter((section: any) =>
    section.items.some((item: string) => linkMap.has(item)),
  );

  if (activeSections.length === 0) return null;

  return (
    <div className="animate-in fade-in slide-in-from-bottom-2 duration-300 p-4 bg-muted/30 rounded-lg border">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {activeSections.map((section: any) => {
          const visibleItems = section.items.filter((item: string) => linkMap.has(item));
          if (visibleItems.length === 0) return null;

          return (
            <div key={section.label} className="flex flex-col gap-2">
              <h3 className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground px-1">
                {section.label}
              </h3>
              <div className="flex flex-col gap-1.5">
                {visibleItems.map((item: string) => {
                  const link = linkMap.get(item);
                  const hasCount = link.count > 0 || link.open_count > 0;
                  const isLinkDisabled =
                    internalLinks[item] && (!link.names || link.names.length === 0);

                  return (
                    <div
                      key={link.doctype}
                      className={`group flex items-center justify-between p-2 rounded-lg border transition-all text-xs h-9 ${
                        hasCount
                          ? "bg-card border-border shadow-sm hover:border-primary/30 hover:shadow-md"
                          : "bg-muted/40 border-border/60 hover:bg-card hover:border-primary/30 hover:shadow-md"
                      } ${isLinkDisabled ? "opacity-60 pointer-events-none" : ""}`}
                    >
                      <button
                        onClick={() => {
                          if (!isLinkDisabled) handleNavigateToList(link.doctype);
                        }}
                        className={`font-medium truncate transition-colors max-w-[70%] block text-left bg-transparent border-none cursor-pointer ${
                          isLinkDisabled
                            ? "text-muted-foreground cursor-not-allowed"
                            : "text-foreground hover:text-primary"
                        }`}
                      >
                        {link.doctype}
                      </button>
                      <div className="flex items-center gap-1.5 ml-2 shrink-0">
                        <span
                          className={`font-semibold ${
                            hasCount ? "text-foreground" : "text-muted-foreground"
                          }`}
                        >
                          {link.count || 0}
                        </span>
                        {link.open_count > 0 && (
                          <span className="px-1.5 py-0.5 text-[9px] font-bold text-white bg-destructive rounded-full min-w-4 text-center">
                            {link.open_count > 99 ? "99+" : link.open_count}
                          </span>
                        )}
                        <button
                          onClick={() => handleNavigateToNew(link.doctype)}
                          className="p-1 rounded hover:bg-muted text-muted-foreground hover:text-primary transition-colors bg-transparent border-none cursor-pointer"
                          title={`Create new ${link.doctype}`}
                        >
                          <Plus className="w-3 h-3" />
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default ConnectionDashboard;