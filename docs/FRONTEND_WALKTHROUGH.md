# SacHealth OS frontend walkthrough

This guide explains how the React app in `frontend/` works and why it is built this way. Read it top to bottom once, then use the "How to explain it" section to practise for interviews.

---

## 1. The big picture

The app is a **single-page application (SPA)**. The browser downloads one HTML file and one JavaScript bundle. After that, React draws every screen in the browser and only talks to the server for data (JSON).

```
React page  ──uses──►  query hook  ──calls──►  API function  ──fetch──►  FastAPI
(what you see)        (caching, loading,       (one per endpoint,       (/beds, /triage, …)
                       errors, refetching)      typed request/response)
```

Each layer has one job:

| Layer | Folder | Job |
|-------|--------|-----|
| Pages and components | `src/pages`, `src/components` | Draw the UI and handle user input. They never call `fetch` directly. |
| Query hooks | `src/api/hooks.ts` | Ask TanStack Query for data, cache it, and refresh it after changes. |
| API functions | `src/api/endpoints.ts` | One small function per backend endpoint, e.g. `api.assignBed(bedId, patientId)`. |
| API client | `src/api/client.ts` | The only place that calls `fetch`. Adds the token, turns errors into `ApiError`. |
| Types | `src/api/types.ts` | TypeScript shapes that mirror the Python response models. |

**Why this matters:** if an endpoint changes, I change it in one place. Components stay simple and are easy to test.

---

## 2. Talking to the API

### The typed client (`src/api/client.ts`)

`apiRequest<T>(path, options)` does four things:

1. Builds the URL with query parameters, skipping empty ones (`buildUrl`).
2. Adds `Authorization: Bearer <token>` when the user is signed in.
3. If the response is not 2xx, throws an `ApiError` that carries the HTTP status and FastAPI's `detail` message. FastAPI's validation errors arrive as a list, so `messageFromDetail` joins them into a readable sentence.
4. On a **401** for a signed-in request, it calls `onUnauthorized`, which logs the user out. That covers expired tokens everywhere at once.

The generic `<T>` is the response type, so `api.beds()` returns `Promise<Bed[]>` and the editor autocompletes `bed.status`.

### Types that mirror the backend (`src/api/types.ts`)

`BedStatus` is built from a constant array:

```ts
export const BED_STATUSES = ["Available", "Occupied", "Pending_Discharge", "Cleaning"] as const;
export type BedStatus = (typeof BED_STATUSES)[number];
```

The same array drives the filter buttons and the chart, and the type checker rejects a typo like `"Ocupied"`.

`TriageCreate` uses a **union type** so you must send either `patient_id` or `patient_name`, never both. That is the same rule the API enforces.

---

## 3. Server state with TanStack Query (`src/api/hooks.ts`)

Data from the server is **server state**: it can change without us, it needs loading and error states, and several screens show the same data. TanStack Query handles that, so I don't write `useEffect` + `useState` for every request.

- `useBeds(status)` → `{ data, isPending, isError, error, refetch }`.
- **Query keys** such as `["beds", "Available"]` or `["patients", { q, limit, offset }]` identify cached data. If two components ask for the same key, there is one request.
- **Mutations** (`useAssignBed`, `useCreateTriage`…) send writes. On success they **invalidate** beds, patients, triage and stats, so every screen refreshes itself. Example: after assigning a bed, the dashboard occupancy updates without any extra code.
- `placeholderData: keepPreviousData` keeps the current page of results visible while the next page loads, so the table doesn't flash empty.
- Retries: network blips are retried twice; 4xx errors (e.g. 404, 409) are not, because they will not change (`src/lib/queryClient.ts`).

---

## 4. Authentication

### Where the token lives (`src/auth/tokenStorage.ts`)

After login the JWT goes into `localStorage`, so a page reload keeps you signed in. On read, the code decodes the token's `exp` claim and throws away expired tokens. It does not check the signature; the server checks it on every request.

> **Trade-off to mention in interviews:** `localStorage` is simple but readable by any script on the page, so it depends on the app having no XSS holes. React escapes output by default and there is no `dangerouslySetInnerHTML`. A more locked-down option is an httpOnly cookie set by the server, which would need CSRF protection. For a demo with fake data, `localStorage` is a reasonable, explicit choice.

### AuthContext (`src/auth/AuthContext.tsx`)

`AuthProvider` keeps the token in React state and exposes `{ user, token, isLoading, login, logout }` through `useAuth()`.

- On load, if a token exists, it calls `GET /auth/me` to confirm it and get the user's name. While that runs, `isLoading` is true.
- `login()` calls `POST /auth/login`, saves the token and updates state, and every component re-renders as signed in.
- It wires the API client (`configureApiClient`) so requests read the current token, and any 401 triggers `logout()`.

### Protected routes (`src/auth/RequireAuth.tsx`)

```tsx
if (isLoading) return <LoadingState label="Checking your session…" />;
if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
```

The guard wraps the whole signed-in layout in `App.tsx`. The `from` value lets the login page send you back where you were going (open `/app/beds` signed out → log in → you land on Beds).

> The guard is a UX feature, not security. Security lives on the server: every write endpoint requires a valid JWT.

---

## 5. Routing (`src/App.tsx`)

React Router maps URLs to pages. The app uses `basename="/app"`, so the URL `/app/patients/3` renders the patient page.

**Why `/app`?** FastAPI serves the API and the UI from the same domain. The API already owns `/beds` and `/patients`. If React used those URLs too, a refresh on `/beds` would return JSON instead of the page. Putting the SPA under `/app` avoids the collision. On the backend, `GET /app/{path}` returns real files (JS, CSS) as-is and `index.html` for everything else (the **SPA fallback**), so deep links and refreshes work.

Filters live in the URL (`/app/triage?priority=1`, `/app/patients?q=ana&offset=10`) via `useSearchParams`. You can bookmark or share a filtered view, and the back button works.

---

## 6. Forms and validation

Forms use **React Hook Form** and **Zod**:

- The Zod schema (`src/lib/triageForm.ts`) states the rules once: age 0–130, O₂ 0–100, name required for a new patient, patient required for an existing one. These match the API's limits, so most mistakes are caught before a request is sent. The server still validates everything.
- `integerField()` fixes a classic bug: `Number("")` is `0`, so an empty age field would pass as "0 years old". Empty strings are rejected as "Age is required" first, and only then converted to a number.
- `toTriageRequest()` turns form values into the API body. It's a pure function, so it is unit tested without rendering anything.

### Accessibility

- `FormField` connects each label to its input (`htmlFor` / `id` from `useId`) and links the error message with `aria-describedby`; invalid inputs get `aria-invalid`.
- Results and errors use `role="status"` / `role="alert"` so screen readers announce them.
- Real `<button>`, `<form>`, `<table>`, `<nav>` elements, a "Skip to content" link, visible focus rings, and `aria-pressed` on filter toggles.
- The bar chart prints the numbers as text, so it doesn't depend on colour alone.

---

## 7. Loading, error and empty states

Every data screen handles the three non-happy states with shared components (`src/components/QueryState.tsx`):

- `LoadingState`: spinner with `role="status"`.
- `ErrorState`: the server's message plus a **Try again** button that calls `refetch()`.
- `EmptyState`: a friendly message, e.g. "No patients match "zoe"".

Mutation errors are shown next to the action. For example, a **409** "Bed is Occupied, not Available" appears inside that bed's card.

---

## 8. Page by page

| Page | Key ideas |
|------|-----------|
| **Login** | Zod-validated form, server error shown in an alert, redirect back to `from`. |
| **Dashboard** | One query (`/stats`); totals and occupancy are derived in render, not stored in state. Dependency-free `BarChart` (CSS widths). |
| **Triage** | `TriageForm` switches between new/existing patient with `useWatch`. Existing patients are chosen with `PatientPicker`, which searches the API (`q` + `limit`) instead of loading everyone, so patient #1 is reachable even with thousands of records. The result card links to the patient. `TriageHistory` filters by priority and paginates. |
| **Patients** | Search is **debounced** (`useDebouncedValue`, 300 ms), so typing "zoe" sends one request, not three. When the search settles it is written to the URL (`?q=zoe`) and the page resets to 1, so a reload shows the same results. Register form below. |
| **Patient detail** | Current bed + triage timeline. A 404 shows "Patient not found" instead of a generic error. |
| **Beds** | Status filter chips, a card per bed. The board always loads every bed and filters on the client, so "who is already in a bed" is computed from all beds, not only the visible ones. Available beds offer a searchable picker without those patients; occupied ones offer Discharge. |

---

## 9. Testing (`npm test`)

Tools: **Vitest** (test runner, Jest-compatible), **React Testing Library** (render components and interact like a user), **user-event** (realistic typing and clicking), **jest-dom** (matchers like `toBeDisabled()`).

Principles:

- **Test behaviour, not implementation.** Tests find elements by role and label (`getByRole("button", { name: /sign in/i })`), the way a user or screen reader would. That also checks accessibility.
- **Mock the network at `fetch`.** `mockApi()` in `src/test/utils.tsx` is a tiny fake server keyed by `"METHOD /path"`. Tests assert on what was sent (body and query params) and on what the user sees.
- `renderWithProviders()` gives each test a fresh QueryClient (no shared cache), a MemoryRouter, and the real AuthProvider.

What is covered (38 tests): the API client (URL building, error parsing, Bearer header, 401 logout, network errors), token expiry, form schemas, login validation/success/failure, the route guard (redirect, session check, rejected token), dashboard numbers/bars/retry, the triage form (new and existing patient, validation), history filters synced to the URL, patients pagination/debounced search/registration, bed assign/discharge with a 409, the beds filter never offering a patient who is in a hidden bed, the patient picker reaching a patient outside the first page, UTC parsing of timestamps, and pagination edge cases.

Also in CI: **ESLint** (React hooks rules, zero warnings), **TypeScript strict mode** (`noUncheckedIndexedAccess` included), and a production **build**.

---

## 10. Build and deploy

- `npm run dev`: Vite dev server on `:5173`. `vite.config.ts` **proxies** `/auth`, `/beds`, … to FastAPI on `:8000`, so the browser sees one origin like in production. CORS also allows `localhost:5173` if you call the API directly.
- `npm run build`: type-checks, then writes static files to `frontend/dist` (`base: "/app/"` makes asset URLs start with `/app/`).
- In production, **one Render web service** does it all. The build command runs `pip install …` and then `npm ci && npm run build`; FastAPI serves `frontend/dist` at `/app`, the API at its usual paths, and `/` redirects to `/app/`. If the build is missing, `/` falls back to the classic page.

---

## 11. How to explain it (interview practice)

**"Walk me through the architecture."**
> "It's a React + TypeScript SPA served by the same FastAPI service as the API. Pages use TanStack Query hooks, the hooks call a small typed API client, and the client is the only place that touches fetch. It attaches the JWT and turns errors into a typed ApiError. Auth state lives in a context, and a route guard protects the signed-in pages."

**"Why TanStack Query instead of useEffect?"**
> "Server data needs caching, loading and error states, de-duplication and refreshing after writes. TanStack Query gives me that with query keys and invalidation. After assigning a bed I invalidate beds, patients and stats, and the dashboard updates by itself."

**"How do you handle auth and expired tokens?"**
> "The token is stored in localStorage and checked against /auth/me on load. Any 401 from the API calls logout globally. The route guard is only UX; the server enforces auth on every protected endpoint. I'd consider httpOnly cookies for a real product because of XSS."

**"How did you test it?"**
> "With React Testing Library I test what the user sees: I query by role and label and mock fetch with a small fake server. For example, the triage test fills the form, submits, checks the exact JSON body sent, and checks that the recommendation is announced."

**"Something you'd improve?"**
> "Show patient names in the triage history (the API returns only IDs, so I'd add a join or an include parameter), add optimistic updates for bed assignment, end-to-end tests with Playwright, and generate the TypeScript types from the OpenAPI schema so they can't drift."

---

## 12. Glossary

- **SPA**: single-page application; one HTML page, React swaps the content.
- **JWT**: signed token proving who you are; sent as `Authorization: Bearer …`.
- **Query key**: the cache "address" of a piece of server data in TanStack Query.
- **Invalidate**: mark cached data as stale so it is fetched again.
- **UTC timestamps**: SQLite returns times without an offset (`2026-11-20T04:00:00`); `parseApiDate` treats those as UTC so they show in the viewer's local time, like PostgreSQL's.
- **Debounce**: wait until the user stops typing before acting.
- **SPA fallback**: the server returns `index.html` for unknown `/app/*` URLs so the router can handle them.
- **Proxy (Vite)**: in development, forwards API calls from `:5173` to `:8000`.
