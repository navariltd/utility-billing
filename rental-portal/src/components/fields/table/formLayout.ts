"use client";

import type { DoctypeField, FormSection, FormTab } from "./types";

/**
 * Build a Frappe-style tab/section/column layout from a flat field list.
 * Propagates collapsible/collapsed state from Section Break fields.
 */
export function buildFormLayout(allFields: DoctypeField[]): FormTab[] {
  const tabs: FormTab[] = [];
  let currentTab: FormTab = { label: "Default", sections: [] };
  let currentSection: FormSection = {
    label: "",
    collapsible: false,
    collapsed: false,
    columns: [{ fields: [] }],
  };

  const flushSection = () => {
    const hasContent =
      currentSection.columns.some((c) => c.fields.length > 0) ||
      currentSection.label !== "";
    if (hasContent) {
      while (
        currentSection.columns.length > 1 &&
        currentSection.columns[currentSection.columns.length - 1].fields
          .length === 0
      ) {
        currentSection.columns.pop();
      }
      currentTab.sections.push(currentSection);
    }
    currentSection = {
      label: "",
      collapsible: false,
      collapsed: false,
      columns: [{ fields: [] }],
    };
  };

  const flushTab = () => {
    flushSection();
    if (currentTab.sections.length > 0 || currentTab.label !== "Default") {
      tabs.push(currentTab);
    }
    currentTab = { label: "Default", sections: [] };
    currentSection = {
      label: "",
      collapsible: false,
      collapsed: false,
      columns: [{ fields: [] }],
    };
  };

  for (const field of allFields) {
    const ft = field.fieldtype;
    if (ft === "Tab Break") {
      flushTab();
      currentTab = {
        label: field.label || field.fieldname || "Default",
        sections: [],
      };
      currentSection = {
        label: "",
        collapsible: false,
        collapsed: false,
        columns: [{ fields: [] }],
      };
    } else if (ft === "Section Break") {
      flushSection();
      currentSection = {
        label: field.label || "",
        collapsible: field.collapsible === 1,
        collapsed: field.collapsed === 1,
        columns: [{ fields: [] }],
      };
    } else if (ft === "Column Break") {
      currentSection.columns.push({ fields: [] });
    } else if (
      ft === "Tab" ||
      ft === "Heading" ||
      ft === "Fold"
    ) {
      continue;
    } else {
      const lastCol = currentSection.columns[currentSection.columns.length - 1];
      lastCol.fields.push(field as any);
    }
  }

  flushTab();
  return tabs;
}