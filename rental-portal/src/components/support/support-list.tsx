/** Support ticket list with search, status filters and quick statistics. */

"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { formatDate } from "@/lib/format";
import type { SupportCounts, SupportIssue } from "@/types/support";
import {
  CheckCircle2,
  ChevronRight,
  Clock3,
  LifeBuoy,
  MessageSquare,
  Plus,
  Search,
} from "lucide-react";
import { useMemo, useState } from "react";
import type { ReactNode } from "react";
import { supportPriorityDot, supportStatusClass } from "./support-utils";

type StatusFilter = "all" | "open" | "resolved";

interface SupportListProps {
  issues: SupportIssue[];
  counts: SupportCounts;
  isLoading: boolean;
  error?: { message?: string } | null;
  onRetry: () => void;
  onSelect: (name: string) => void;
  onCreate: () => void;
}

const FILTERS: { value: StatusFilter; label: string }[] = [
  { value: "all", label: "All" },
  { value: "open", label: "Open" },
  { value: "resolved", label: "Resolved" },
];

export function SupportList({
  issues,
  counts,
  isLoading,
  error,
  onRetry,
  onSelect,
  onCreate,
}: SupportListProps) {
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<StatusFilter>("all");

  const visibleIssues = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return issues.filter((issue) => {
      if (filter === "open" && !issue.is_open) return false;
      if (filter === "resolved" && issue.is_open) return false;
      if (!needle) return true;

      return [issue.name, issue.subject, issue.issue_type, issue.priority]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(needle));
    });
  }, [filter, issues, query]);

  if (error) {
    return (
      <div className="flex flex-col items-center gap-3 py-12 text-center">
        <LifeBuoy className="text-muted-foreground h-7 w-7" />
        <p className="text-muted-foreground text-sm">
          {error.message || "Could not load your support requests."}
        </p>
        <Button size="sm" variant="outline" className="cursor-pointer" onClick={onRetry}>
          Try again
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <div className="grid gap-3 sm:grid-cols-3">
        <StatCard
          label="Open"
          value={counts.open}
          icon={<Clock3 className="h-4 w-4" />}
          className="text-sky-600 dark:text-sky-400"
        />
        <StatCard
          label="Replied"
          value={counts.replied}
          icon={<MessageSquare className="h-4 w-4" />}
          className="text-violet-600 dark:text-violet-400"
        />
        <StatCard
          label="Resolved"
          value={counts.resolved}
          icon={<CheckCircle2 className="h-4 w-4" />}
          className="text-emerald-600 dark:text-emerald-400"
        />
      </div>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative w-full sm:max-w-xs">
          <Search className="text-muted-foreground pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2" />
          <Input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search requests"
            className="pl-9"
            aria-label="Search support requests"
          />
        </div>
        <div className="flex flex-wrap items-center gap-1">
          {FILTERS.map((option) => (
            <Button
              key={option.value}
              type="button"
              size="sm"
              variant={filter === option.value ? "secondary" : "ghost"}
              className="cursor-pointer"
              onClick={() => setFilter(option.value)}
            >
              {option.label}
            </Button>
          ))}
          <Button
            type="button"
            size="sm"
            className="ml-1 cursor-pointer"
            onClick={onCreate}
          >
            <Plus className="mr-1.5 h-4 w-4" />
            New request
          </Button>
        </div>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          <Skeleton className="h-24 w-full rounded-xl" />
          <Skeleton className="h-24 w-full rounded-xl" />
        </div>
      ) : visibleIssues.length === 0 ? (
        <EmptyState hasIssues={issues.length > 0} onCreate={onCreate} />
      ) : (
        <ul className="space-y-3">
          {visibleIssues.map((issue) => (
            <li key={issue.name}>
              <button
                type="button"
                onClick={() => onSelect(issue.name)}
                className="bg-card hover:border-primary/40 hover:bg-accent/30 focus-visible:ring-ring group flex w-full cursor-pointer items-start gap-4 rounded-xl border p-4 text-left transition-colors focus-visible:ring-2 focus-visible:outline-none"
              >
                <div className="min-w-0 flex-1 space-y-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant="outline" className={supportStatusClass(issue.status)}>
                      {issue.status}
                    </Badge>
                    {issue.issue_type ? (
                      <span className="text-muted-foreground text-xs">
                        {issue.issue_type}
                      </span>
                    ) : null}
                    {issue.priority ? (
                      <span className="text-muted-foreground inline-flex items-center gap-1.5 text-xs">
                        <span
                          className={`h-1.5 w-1.5 rounded-full ${supportPriorityDot(issue.priority)}`}
                        />
                        {issue.priority}
                      </span>
                    ) : null}
                  </div>
                  <div>
                    <p className="truncate font-medium">{issue.subject}</p>
                    <p className="text-muted-foreground mt-0.5 text-xs">
                      {issue.name} · opened {formatDate(issue.creation)}
                    </p>
                  </div>
                  {issue.snippet ? (
                    <p className="text-muted-foreground line-clamp-2 text-sm">
                      {issue.snippet}
                    </p>
                  ) : null}
                </div>
                <ChevronRight className="text-muted-foreground group-hover:text-foreground mt-1 h-4 w-4 shrink-0 transition-colors" />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function StatCard({
  label,
  value,
  icon,
  className,
}: {
  label: string;
  value: number;
  icon: ReactNode;
  className?: string;
}) {
  return (
    <div className="bg-muted/30 flex items-center gap-3 rounded-xl border p-3">
      <span className={`bg-background rounded-lg border p-2 ${className ?? ""}`}>
        {icon}
      </span>
      <div>
        <p className="text-xl leading-none font-semibold">{value}</p>
        <p className="text-muted-foreground mt-1 text-xs">{label}</p>
      </div>
    </div>
  );
}

function EmptyState({
  hasIssues,
  onCreate,
}: {
  hasIssues: boolean;
  onCreate: () => void;
}) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed px-6 py-12 text-center">
      <div className="bg-primary/10 text-primary rounded-full p-3">
        <LifeBuoy className="h-6 w-6" />
      </div>
      <div className="space-y-1">
        <p className="font-medium">
          {hasIssues ? "No requests match your filters" : "No support requests yet"}
        </p>
        <p className="text-muted-foreground max-w-sm text-sm">
          {hasIssues
            ? "Try a different search term or status filter."
            : "Raise a request for maintenance, billing, access or anything else about this tenancy."}
        </p>
      </div>
      {!hasIssues ? (
        <Button size="sm" className="cursor-pointer" onClick={onCreate}>
          <Plus className="mr-1.5 h-4 w-4" />
          Raise a request
        </Button>
      ) : null}
    </div>
  );
}
