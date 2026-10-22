/**
 * Property booking placeholder.
 *
 * Booking (deposit invoice, payment link and calendar sync) is delivered in the
 * next phase; this page keeps the protected booking route working meanwhile.
 */

import { BaseLayout } from "@/components/layouts/base-layout";
import { Card, CardContent } from "@/components/ui/card";
import { Construction } from "lucide-react";
import { useParams } from "react-router-dom";

export default function PropertyBooking() {
  const { property } = useParams<{ property: string }>();

  return (
    <BaseLayout
      title={`Book ${property ? decodeURIComponent(property) : "property"}`}
      description="Reserve this unit"
    >
      <div className="px-4 lg:px-6">
        <Card>
          <CardContent className="text-muted-foreground flex flex-col items-center gap-2 py-16 text-sm">
            <Construction className="h-6 w-6" />
            Online booking, the deposit invoice and mobile money payment are coming
            in the next release.
          </CardContent>
        </Card>
      </div>
    </BaseLayout>
  );
}

