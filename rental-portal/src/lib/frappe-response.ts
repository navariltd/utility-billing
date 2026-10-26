/** Helpers for working with Frappe method responses. */

/**
 * Frappe wraps method results in a `message` envelope, while some SDK helpers
 * return the envelope and others return the unwrapped value.
 */
export type FrappeMethodResponse<T> = T | { message: T };

/** Return the method result whether or not it is wrapped in `message`. */
export function unwrapMethodResponse<T>(
  response: FrappeMethodResponse<T>,
): T {
  if (response && typeof response === "object" && "message" in response) {
    return (response as { message: T }).message;
  }

  return response as T;
}
