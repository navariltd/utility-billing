import {
  useFrappeCreateDoc,
  useFrappeDeleteCall,
  useFrappeDeleteDoc,
  useFrappeFileUpload,
  useFrappeGetCall,
  useFrappeGetDoc,
  useFrappeGetDocCount,
  useFrappeGetDocList,
  useFrappePostCall,
  useFrappePutCall,
  useFrappeUpdateDoc,
  useSearch,
} from "frappe-react-sdk";

import type {
  FileArgs,
  Filter,
  FrappeDoc,
  FrappeError,
  FrappeFileUploadResponse,
  GetDocListArgs,
  SearchResult,
} from "frappe-react-sdk";

export type Key = string | any[] | null | (() => string | any[] | null);

export interface SWRConfiguration {
  revalidateOnFocus?: boolean;
  revalidateOnReconnect?: boolean;
  refreshInterval?: number;
  refreshWhenHidden?: boolean;
  refreshWhenOffline?: boolean;
  shouldRetryOnError?: boolean;
  dedupingInterval?: number;
  focusThrottleInterval?: number;
  loadingTimeout?: number;
  errorRetryInterval?: number;
  errorRetryCount?: number;
  fallbackData?: any;
  suspense?: boolean;
  keepPreviousData?: boolean;
  [key: string]: any;
}

export interface ApiResponse<T = any> {
  data?: T;
  error?: FrappeError | null;
  isLoading?: boolean;
  isValidating?: boolean;
  mutate?: () => void;
}

export interface MutationResponse {
  loading: boolean;
  error: FrappeError | null | undefined;
  isCompleted: boolean;
  reset: () => void;
}

export type {
  FileArgs,
  Filter,
  FrappeDoc,
  FrappeFileUploadResponse,
  GetDocListArgs,
  SearchResult,
};

/**
 * Get a single document by doctype and name
 * Similar to frappe.client.get
 */
export const useGetDoc = <T = any>(
  doctype: string,
  name?: string,
  swrKey?: Key,
  options?: SWRConfiguration,
) => {
  return useFrappeGetDoc<T>(doctype, name, swrKey, options);
};

/**
 * Get a list of documents with filters, sorting, and pagination
 * Similar to frappe.client.get_list
 */
export const useGetList = <T = any, K = FrappeDoc<T>>(
  doctype: string,
  args?: GetDocListArgs<K>,
  swrKey?: Key,
  options?: SWRConfiguration,
) => {
  return useFrappeGetDocList<T, K>(doctype, args, swrKey, options);
};

/**
 * Get count of documents with optional filters
 * Similar to frappe.client.get_count
 */
export const useGetCount = <T = any>(
  doctype: string,
  filters?: Filter<T>[],
  debug?: boolean,
  swrKey?: Key,
  options?: SWRConfiguration,
) => {
  return useFrappeGetDocCount<T>(doctype, filters, debug, swrKey, options);
};

/**
 * Create a new document
 * Similar to frappe.client.insert
 */
export const useInsertDoc = <T = any>() => {
  const { createDoc, loading, error, isCompleted, reset } =
    useFrappeCreateDoc<T>();

  const insert = async (doctype: string, doc: T): Promise<FrappeDoc<T>> => {
    return await createDoc(doctype, doc);
  };

  return {
    insert,
    loading,
    error,
    isCompleted,
    reset,
  };
};

/**
 * Update an existing document
 * Similar to frappe.client.set_value or frappe.client.save
 */
export const useUpdateDoc = <T = any>() => {
  const { updateDoc, loading, error, isCompleted, reset } =
    useFrappeUpdateDoc<T>();

  const update = async (
    doctype: string,
    docname: string | null,
    doc: Partial<T>,
  ): Promise<FrappeDoc<T>> => {
    return await updateDoc(doctype, docname, doc);
  };

  return {
    update,
    loading,
    error,
    isCompleted,
    reset,
  };
};

/**
 * Delete a document
 * Similar to frappe.client.delete
 */
export const useDeleteDoc = () => {
  const { deleteDoc, loading, error, isCompleted, reset } =
    useFrappeDeleteDoc();

  const remove = async (doctype: string, docname?: string | null) => {
    return await deleteDoc(doctype, docname);
  };

  return {
    remove,
    loading,
    error,
    isCompleted,
    reset,
  };
};

/**
 * Make a GET API call to a Frappe method
 * Similar to frappe.call with GET method
 */
export const useCallGet = <T = any>(
  method: string,
  params?: Record<string, any>,
  swrKey?: Key,
  options?: SWRConfiguration,
  type?: "GET" | "POST",
) => {
  return useFrappeGetCall<T>(method, params, swrKey, options, type);
};

/**
 * Make a POST API call to a Frappe method
 * Similar to frappe.call with POST method
 */
export const useCallPost = <T = any>(method: string) => {
  const { call, result, loading, error, isCompleted, reset } =
    useFrappePostCall<T>(method);

  const post = async (params: Record<string, any>): Promise<T> => {
    return await call(params);
  };

  return {
    post,
    result,
    loading,
    error,
    isCompleted,
    reset,
  };
};

/**
 * Make a PUT API call to a Frappe method
 * Similar to frappe.call with PUT method
 */
export const useCallPut = <T = any>(method: string) => {
  const { call, result, loading, error, isCompleted, reset } =
    useFrappePutCall<T>(method);

  const put = async (params: Record<string, any>): Promise<T> => {
    return await call(params);
  };

  return {
    put,
    result,
    loading,
    error,
    isCompleted,
    reset,
  };
};

/**
 * Make a DELETE API call to a Frappe method
 * Similar to frappe.call with DELETE method
 */
export const useCallDelete = <T = any>(method: string) => {
  const { call, result, loading, error, isCompleted, reset } =
    useFrappeDeleteCall<T>(method);

  const del = async (params: Record<string, any>): Promise<T> => {
    return await call(params);
  };

  return {
    delete: del,
    result,
    loading,
    error,
    isCompleted,
    reset,
  };
};

/**
 * Upload a file to Frappe
 * Similar to frappe.upload_file
 */
export const useUploadFile = <T = any>() => {
  const { upload, progress, loading, error, isCompleted, reset } =
    useFrappeFileUpload<T>();

  const uploadFile = async (
    file: File,
    args: FileArgs<T>,
    apiPath?: string,
  ): Promise<FrappeFileUploadResponse> => {
    return await upload(file, args, apiPath);
  };

  return {
    uploadFile,
    progress,
    loading,
    error,
    isCompleted,
    reset,
  };
};

/**
 * Search for documents in Frappe (v15+)
 * Similar to frappe.search
 */
export const useSearchDocs = (
  doctype: string,
  text: string,
  filters?: Filter[],
  limit?: number,
  debounce?: number,
) => {
  return useSearch(doctype, text, filters, limit, debounce);
};

/**
 * Build a query string for DocList args
 */
export const buildQuery = (args?: GetDocListArgs): string => {
  if (!args) return "";

  const queryParts: string[] = [];

  if (args.fields) {
    queryParts.push(`fields=${JSON.stringify(args.fields)}`);
  }

  if (args.filters) {
    queryParts.push(`filters=${JSON.stringify(args.filters)}`);
  }

  if (args.orderBy) {
    let orderByStr: string;
    if (typeof args.orderBy === "string") {
      orderByStr = args.orderBy;
    } else {
      const field = String(args.orderBy.field);
      const order = args.orderBy.order || "asc";
      orderByStr = `${field} ${order}`;
    }
    queryParts.push(`order_by=${orderByStr}`);
  }

  if (args.limit) {
    queryParts.push(`limit=${args.limit}`);
  }

  if (args.limit_start) {
    queryParts.push(`limit_start=${args.limit_start}`);
  }

  if (args.groupBy) {
    queryParts.push(`group_by=${String(args.groupBy)}`);
  }

  return queryParts.length > 0 ? `?${queryParts.join("&")}` : "";
};

/**
 * Build filters for DocList queries
 */
export const buildFilters = <T = any>(
  conditions: Array<{
    field: keyof T | string;
    operator:
      | "="
      | "!="
      | ">"
      | "<"
      | ">="
      | "<="
      | "like"
      | "in"
      | "not in"
      | "between";
    value: any;
  }>,
): Filter<T>[] => {
  return conditions.map(
    (condition) =>
      [
        condition.field as string,
        condition.operator,
        condition.value,
      ] as Filter<T>,
  );
};

/**
 * Create a filter for a single field
 */
export const createFilter = <T = any>(
  field: keyof T | string,
  operator:
    | "="
    | "!="
    | ">"
    | "<"
    | ">="
    | "<="
    | "like"
    | "in"
    | "not in"
    | "between",
  value: any,
): Filter<T> => {
  return [field as string, operator, value] as Filter<T>;
};

export default {
  useGetDoc,
  useGetList,
  useGetCount,
  useInsertDoc,
  useUpdateDoc,
  useDeleteDoc,
  useCallGet,
  useCallPost,
  useCallPut,
  useCallDelete,
  useUploadFile,
  useSearchDocs,
  buildQuery,
  buildFilters,
  createFilter,
};
