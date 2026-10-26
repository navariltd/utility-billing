/** Shared error message extraction for portal dialogs. */

export function errorMessage(error: unknown, fallback: string): string {
  return (error as { message?: string } | null)?.message ?? fallback;
}
