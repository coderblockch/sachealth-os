/**
 * Persists the JWT in localStorage so a page reload keeps the user signed in.
 * Expired tokens are discarded by reading the `exp` claim (no signature check
 * is needed here: the server validates every request).
 */

const KEY = "sachealth.token";

export function decodeExpiry(token: string): number | null {
  try {
    const payload = token.split(".")[1];
    if (!payload) return null;
    const json = JSON.parse(atob(payload.replace(/-/g, "+").replace(/_/g, "/")));
    return typeof json.exp === "number" ? json.exp * 1000 : null;
  } catch {
    return null;
  }
}

export function isExpired(token: string, now = Date.now()): boolean {
  const expiry = decodeExpiry(token);
  return expiry !== null && expiry <= now;
}

export const tokenStorage = {
  get(): string | null {
    const token = localStorage.getItem(KEY);
    if (token && isExpired(token)) {
      localStorage.removeItem(KEY);
      return null;
    }
    return token;
  },
  set(token: string) {
    localStorage.setItem(KEY, token);
  },
  clear() {
    localStorage.removeItem(KEY);
  },
};
