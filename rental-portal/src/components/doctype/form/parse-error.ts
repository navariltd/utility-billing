/**
 * parse-error – utilities for extracting human-readable error messages from Frappe API responses.
 *
 * Key dependencies: used by form and list components to surface meaningful error text to users.
 * Handles Frappe SDK error shapes including _server_messages, exception, and httpStatus fields.
 */

/** Extract a readable error message from a Frappe SDK error object. */
export function parseFrappeError(err: any): string {
  if (err?._server_messages) {
    try {
      const messages = JSON.parse(err._server_messages);
      if (Array.isArray(messages) && messages.length > 0) {
        const first =
          typeof messages[0] === "string" ? JSON.parse(messages[0]) : messages[0];
        return first?.message || first?.title || err?.message || "An error occurred";
      }
    } catch {
      // Parsing _server_messages can throw if malformed; fall through to other checks
    }
  }
  if (err?.messages && Array.isArray(err.messages) && err.messages.length > 0) {
    return err.messages[0];
  }
  if (err?.exception) return err.exception;
  if (err?.message) return err.message;
  return "An error occurred";
}

/**
 * Check whether a Frappe SDK error object indicates a 403 / PermissionError.
 *
 * Args:
 *   err: The error object from a Frappe API call.
 *
 * Returns:
 *   True if the error is a permission error (403 status or matching text).
 */
export function isPermissionError(err: any): boolean {
  if (!err) return false;
  if (err.httpStatus === 403 || err.status === 403) return true;
  const msg =
    (err.exception as string) ||
    (err.message as string) ||
    (err.title as string) ||
    "";
  return (
    msg.includes("403") ||
    msg.includes("PermissionError") ||
    msg.toLowerCase().includes("forbidden") ||
    msg.toLowerCase().includes("not permitted")
  );
}
