/**
 * Small typed wrapper around fetch.
 *
 * - Adds the JWT as a Bearer token when one is available.
 * - Turns non-2xx responses into an ApiError with FastAPI's `detail` message.
 * - Calls `onUnauthorized` on 401 so the auth layer can log the user out.
 */

export class ApiError extends Error {
  readonly status: number;
  readonly detail: unknown;

  constructor(status: number, message: string, detail?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

type TokenGetter = () => string | null;

let getToken: TokenGetter = () => null;
let onUnauthorized: () => void = () => {};

/** Wired up once by AuthProvider. */
export function configureApiClient(options: { getToken: TokenGetter; onUnauthorized: () => void }) {
  getToken = options.getToken;
  onUnauthorized = options.onUnauthorized;
}

/** FastAPI returns `detail` as a string, or as a list of validation errors. */
export function messageFromDetail(detail: unknown, fallback: string): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => (item && typeof item === "object" && "msg" in item ? String(item.msg) : null))
      .filter(Boolean);
    if (messages.length) return messages.join("; ");
  }
  return fallback;
}

export type QueryParams = Record<string, string | number | undefined | null>;

export function buildUrl(path: string, params?: QueryParams): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params ?? {})) {
    if (value !== undefined && value !== null && value !== "") search.set(key, String(value));
  }
  const query = search.toString();
  return query ? `${path}?${query}` : path;
}

export async function apiRequest<T>(
  path: string,
  options: { method?: string; body?: unknown; params?: QueryParams; auth?: boolean } = {},
): Promise<T> {
  const { method = "GET", body, params, auth = true } = options;
  const headers: Record<string, string> = { Accept: "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const token = auth ? getToken() : null;
  if (token) headers.Authorization = `Bearer ${token}`;

  let response: Response;
  try {
    response = await fetch(buildUrl(path, params), {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError(0, "Cannot reach the server. Check your connection and try again.");
  }

  if (response.status === 204) return undefined as T;

  const data: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = data && typeof data === "object" && "detail" in data ? data.detail : undefined;
    if (response.status === 401 && token) onUnauthorized();
    throw new ApiError(response.status, messageFromDetail(detail, `Request failed (${response.status})`), detail);
  }
  return data as T;
}
