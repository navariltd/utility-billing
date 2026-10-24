/** Shared error message extraction for booking dialogs. */

export function errorMessage(error: unknown, fallback: string): string {
  return (error as { message?: string } | null)?.message ?? fallback;
}
