"use client";

import * as React from "react";
import { FrappeField } from "./FrappeField";
import type { FrappeFieldMeta } from "./FrappeField";

/**
 * Example usage of the FrappeField component
 * This demonstrates how to render Frappe DocType fields in React
 */

export const FrappeFieldExample = () => {
  const [formData, setFormData] = React.useState<Record<string, any>>({
    customer_name: "",
    customer_type: "Individual",
    customer_group: "Commercial",
    credit_limit: 5000,
    is_active: true,
    notes: "",
    created_at: null,
  });

  // Example field definitions from a Frappe DocType
  const fields: FrappeFieldMeta[] = [
    {
      fieldname: "customer_name",
      label: "Customer Name",
      fieldtype: "Data",
      required: true,
      placeholder: "Enter customer name",
      max_length: 100,
    },
    {
      fieldname: "customer_type",
      label: "Customer Type",
      fieldtype: "Select",
      options: "Individual\nCommercial\nGovernment",
      required: true,
    },
    {
      fieldname: "customer_group",
      label: "Customer Group",
      fieldtype: "Link",
      options: "Customer Group",
    },
    {
      fieldname: "credit_limit",
      label: "Credit Limit",
      fieldtype: "Currency",
      precision: 2,
    },
    {
      fieldname: "is_active",
      label: "Active",
      fieldtype: "Check",
      default: 1,
    },
    {
      fieldname: "notes",
      label: "Notes",
      fieldtype: "Long Text",
      placeholder: "Enter any additional notes...",
    },
    {
      fieldname: "created_at",
      label: "Created At",
      fieldtype: "Datetime",
      read_only: true,
    },
    {
      fieldname: "contact_info",
      label: "Contact Information",
      fieldtype: "Fold",
    },
    {
      fieldname: "address",
      label: "Address",
      fieldtype: "Section Break",
    },
    {
      fieldname: "address_line1",
      label: "Address Line 1",
      fieldtype: "Data",
    },
    {
      fieldname: "city",
      label: "City",
      fieldtype: "Data",
    },
    {
      fieldname: "country",
      label: "Country",
      fieldtype: "Link",
      options: "Country",
    },
  ];

  const handleChange = (value: any, fieldname?: string) => {
    if (!fieldname) return;
    setFormData((prev) => ({
      ...prev,
      [fieldname]: value,
    }));
    console.log(`Field ${fieldname} changed to:`, value);
  };

  const handleSubmit = () => {
    console.log("Form data:", formData);
    alert("Form submitted! Check console for data.");
  };

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <div className="space-y-2">
        <h1 className="text-3xl font-bold">FrappeField Example</h1>
        <p className="text-muted-foreground">
          This demonstrates the FrappeField component that emulates Frappe field types using shadcn/ui components.
        </p>
      </div>

      <div className="border rounded-lg p-6 space-y-4 bg-background">
        <h2 className="text-xl font-semibold">Customer Form</h2>
        
        {fields.map((field) => (
          <FrappeField
            key={field.fieldname}
            field={field}
            value={formData[field.fieldname]}
            onChange={handleChange}
            doctype="Customer"
            className="max-w-md"
          />
        ))}

        <div className="flex gap-2 pt-4">
          <button
            type="button"
            onClick={handleSubmit}
            className="inline-flex items-center justify-center gap-2 rounded-md text-sm font-medium transition-all disabled:pointer-events-none disabled:opacity-50 bg-primary text-primary-foreground shadow-xs hover:bg-primary/90 h-9 px-4 py-2"
          >
            Submit Form
          </button>
          <button
            type="button"
            onClick={() => setFormData({})}
            className="inline-flex items-center justify-center gap-2 rounded-md text-sm font-medium transition-all disabled:pointer-events-none disabled:opacity-50 border bg-background shadow-xs hover:bg-accent hover:text-accent-foreground h-9 px-4 py-2"
          >
            Reset
          </button>
        </div>
      </div>

      <div className="border rounded-lg p-6 space-y-4 bg-muted/20">
        <h3 className="font-semibold">Current Form Data:</h3>
        <pre className="text-xs bg-background p-4 rounded-md overflow-auto">
          {JSON.stringify(formData, null, 2)}
        </pre>
      </div>
    </div>
  );
};

export default FrappeFieldExample;