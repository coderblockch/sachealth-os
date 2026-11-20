import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import type { ReactElement } from "react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { vi } from "vitest";

import { AuthProvider } from "../auth/AuthContext";

/** A fake JWT whose payload has the given expiry (seconds since epoch). */
export function fakeToken(expSeconds = Math.floor(Date.now() / 1000) + 3600) {
  const payload = btoa(JSON.stringify({ sub: "1", exp: expSeconds }));
  return `header.${payload}.signature`;
}

export const demoUser = { id: 1, email: "demo@sachealth.dev", full_name: "Demo Clinician" };

type Handler = (request: { url: URL; method: string; body: unknown; headers: Headers }) => {
  status?: number;
  json?: unknown;
};

/**
 * Replaces global fetch with a tiny router: keys are "METHOD /path".
 * Returns the mock so tests can assert on calls.
 */
export function mockApi(routes: Record<string, Handler | object>) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(String(input), "http://localhost");
    const method = (init?.method ?? "GET").toUpperCase();
    const key = `${method} ${url.pathname}`;
    const route = routes[key];
    if (!route) return new Response(JSON.stringify({ detail: `No mock for ${key}` }), { status: 500 });
    const body = init?.body ? JSON.parse(String(init.body)) : undefined;
    const result =
      typeof route === "function"
        ? (route as Handler)({ url, method, body, headers: new Headers(init?.headers) })
        : { json: route };
    const status = result.status ?? 200;
    return new Response(status === 204 ? null : JSON.stringify(result.json ?? null), {
      status,
      headers: { "Content-Type": "application/json" },
    });
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

/** Calls made to a path, with parsed query params and JSON body. */
export function callsTo(fetchMock: ReturnType<typeof mockApi>, method: string, path: string) {
  return fetchMock.mock.calls
    .map(([input, init]) => ({ url: new URL(String(input), "http://localhost"), init }))
    .filter(({ url, init }) => url.pathname === path && (init?.method ?? "GET").toUpperCase() === method)
    .map(({ url, init }) => ({
      params: Object.fromEntries(url.searchParams),
      body: init?.body ? JSON.parse(String(init.body)) : undefined,
      headers: new Headers(init?.headers),
    }));
}

function LocationProbe() {
  const location = useLocation();
  return <div data-testid="location">{location.pathname + location.search}</div>;
}

export function renderWithProviders(
  ui: ReactElement,
  { route = "/", path = "*", signedIn = false }: { route?: string; path?: string; signedIn?: boolean } = {},
) {
  if (signedIn) localStorage.setItem("sachealth.token", fakeToken());
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[route]}>
        <AuthProvider>
          <Routes>
            <Route path={path} element={ui} />
            <Route path="/login" element={<div>Login screen</div>} />
          </Routes>
          <LocationProbe />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}
