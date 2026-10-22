/**
 * Dynamic doctype detail/form page.
 *
 * Rendered inside `BaseLayout` so the portal sidebar and header stay visible
 * while viewing or editing a record through the generic `/app/:doctype/:id`
 * route.
 */

"use client";

import { BaseLayout } from "@/components/layouts/base-layout";
import { DocTypeForm } from "@/components/doctype";
import { slugToDoctype } from "@/lib/doctype-map";
import { useParams } from "react-router-dom";

export default function AppDetailPage() {
  const { doctype: slug, id } = useParams<{ doctype: string; id: string }>();
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
      <DocTypeForm
        doctype={doctype}
        docname={id === "new" ? undefined : id}
        forceNew={id === "new"}
      />
    </BaseLayout>
  );
}
