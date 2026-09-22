import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";

/**
 * A hook that persists state to sessionStorage keyed by the current route path.
 * This preserves page state across navigations - when the user leaves and returns
 * to the page, their state (form inputs, selections, fetched data) is restored.
 *
 * @param key - A unique key for this piece of state within the page
 * @param defaultValue - The default value when no persisted state exists
 * @returns A stateful value and setter, same as useState
 */
export function usePageState<T>(
  key: string,
  defaultValue: T,
): [T, (value: T | ((prev: T) => T)) => void] {
  const location = useLocation();
  const storageKey = `${location.pathname}:${key}`;

  const [state, setState] = useState<T>(() => {
    try {
      const stored = sessionStorage.getItem(storageKey);
      if (stored !== null) {
        return JSON.parse(stored);
      }
    } catch {
      // Ignore parse errors, use default
    }
    return defaultValue;
  });

  // Persist state to sessionStorage whenever it changes
  useEffect(() => {
    try {
      sessionStorage.setItem(storageKey, JSON.stringify(state));
    } catch {
      // Ignore storage quota errors
    }
  }, [storageKey, state]);

  return [state, setState];
}

/**
 * Clears all persisted state for a given page path.
 * Useful for "Reset" or "Clear" actions.
 */
export function clearPageState(pathname: string) {
  const prefix = `${pathname}:`;
  try {
    const keysToRemove: string[] = [];
    for (let i = 0; i < sessionStorage.length; i++) {
      const key = sessionStorage.key(i);
      if (key && key.startsWith(prefix)) {
        keysToRemove.push(key);
      }
    }
    keysToRemove.forEach((key) => sessionStorage.removeItem(key));
  } catch {
    // Ignore errors
  }
}