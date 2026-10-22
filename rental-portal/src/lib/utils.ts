import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Get the correct URL for public assets using Frappe's approach
 * Serves assets from the standard `/assets/[app_name]/` path format
 */
export function assetUrl(path: string, appName: string = "react-ui"): string {
  const cleanPath = path.startsWith("/") ? path.slice(1) : path;
  return `/assets/${appName}/${cleanPath}`;
}

/**
 * Get the correct URL path with the 'react-ui' basename prefix for internal navigation
 * @param path - The internal path (e.g., "/dashboard", "/auth/sign-in")
 * @returns The full path with the react-ui basename prefix
 */
export function getAppUrl(path: string): string {
  const basename = "/react-ui";
  const cleanPath = path.startsWith("/") ? path : `/${path}`;
  return `${basename}${cleanPath}`;
}
