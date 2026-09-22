/**
 * Dynamic doctype list page.
 *
 * Rendered inside `BaseLayout` so the portal sidebar and header stay visible
 * while browsing doctypes through the generic `/app/:doctype` route.
 */

"use client";

import { BaseLayout } from "@/components/layouts/base-layout";
import { DocTypeList } from "@/components/doctype";
import { slugToDoctype } from "@/lib/doctype-map";
import { useParams } from "react-router-dom";

export default function AppListPage() {
  const { doctype: slug } = useParams<{ doctype: string }>();
  const doctype = slug ? slugToDoctype(slug) : "";

  if (!doctype) {
    return (
      <BaseLayout title="Not found">
        <p className="text-muted-foreground px-4 py-20 text-center lg:px-6">
          No document type specified.
        </p>
      </BaseLayout>
    );
  }

  return (
    <BaseLayout>
      <DocTypeList doctype={doctype} title={doctype} />
    </BaseLayout>
  );
}
