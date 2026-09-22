/**
 * computePaginationPages – generates pagination page numbers with ellipsis for large page counts.
 *
 * Key dependencies: used by DocTypeList to display compact pagination bars.
 * Shows full range for ≤7 pages, first+last with ellipsis for larger ranges.
 */

/**
 * Compute the array of page numbers/ellipsis markers for pagination display.
 *
 * Args:
 *   totalPages: Total number of pages available.
 *   currentPage: The currently active page (1-based).
 *
 * Returns:
 *   Array of page numbers and "..." ellipsis markers.
 */
export function computePaginationPages(totalPages: number, currentPage: number): (number | "...")[] {
  if (totalPages <= 1) return [];
  const p: (number | "...")[] = [];
  if (totalPages <= 7) {
    for (let i = 1; i <= totalPages; i++) p.push(i);
  } else if (currentPage <= 4) {
    for (let i = 1; i <= 5; i++) p.push(i);
    p.push("...");
    p.push(totalPages);
  } else if (currentPage >= totalPages - 3) {
    p.push(1);
    p.push("...");
    for (let i = totalPages - 4; i <= totalPages; i++) p.push(i);
  } else {
    p.push(1);
    p.push("...");
    for (let i = currentPage - 1; i <= currentPage + 1; i++) p.push(i);
    p.push("...");
    p.push(totalPages);
  }
  return p;
}