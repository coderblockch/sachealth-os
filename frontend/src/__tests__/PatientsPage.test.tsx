import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { PatientsPage } from "../pages/PatientsPage";
import { callsTo, mockApi, renderWithProviders } from "../test/utils";

const patient = (id: number, name: string) => ({ id, full_name: name, age: 30 + id, created_at: "2026-11-20T04:00:00Z" });

function patientsApi() {
  const all = Array.from({ length: 12 }, (_, i) => patient(i + 1, i === 11 ? "Zoe Unique" : `Patient ${i + 1}`));
  return mockApi({
    "GET /patients": ({ url }) => {
      const q = (url.searchParams.get("q") ?? "").toLowerCase();
      const limit = Number(url.searchParams.get("limit"));
      const offset = Number(url.searchParams.get("offset"));
      const matches = all.filter((p) => p.full_name.toLowerCase().includes(q));
      return { json: { items: matches.slice(offset, offset + limit), total: matches.length, limit, offset } };
    },
    "POST /patients": ({ body }) => ({ status: 201, json: { id: 99, created_at: "2026-11-20T04:00:00Z", ...(body as object) } }),
  });
}

describe("PatientsPage", () => {
  it("paginates with offset/limit", async () => {
    const fetchMock = patientsApi();
    renderWithProviders(<PatientsPage />, { signedIn: true });
    expect(await screen.findByText("Page 1 of 2 · 12 results")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /next/i }));
    expect(await screen.findByText("Page 2 of 2 · 12 results")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Zoe Unique" })).toHaveAttribute("href", "/patients/12");
    expect(callsTo(fetchMock, "GET", "/patients").at(-1)!.params).toMatchObject({ offset: "10", limit: "10" });
  });

  it("debounces the search and queries the API once", async () => {
    const fetchMock = patientsApi();
    renderWithProviders(<PatientsPage />, { signedIn: true });
    await screen.findByText("Page 1 of 2 · 12 results");
    await userEvent.type(screen.getByRole("searchbox"), "zoe");
    await waitFor(() => expect(screen.getAllByRole("row")).toHaveLength(2)); // header + 1 match
    const searches = callsTo(fetchMock, "GET", "/patients").filter((c) => c.params.q);
    expect(searches.map((c) => c.params.q)).toEqual(["zoe"]);
  });

  it("validates and registers a new patient", async () => {
    const fetchMock = patientsApi();
    renderWithProviders(<PatientsPage />, { signedIn: true });
    const form = screen.getByRole("form", { name: /register patient/i });
    await userEvent.click(screen.getByRole("button", { name: "Register" }));
    expect(await screen.findByText("Name is required")).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText(/full name/i), "Ana Test");
    await userEvent.type(form.querySelector("input[type=number]")!, "41");
    await userEvent.click(screen.getByRole("button", { name: "Register" }));
    expect(await screen.findByText("Registered Ana Test.")).toBeInTheDocument();
    expect(callsTo(fetchMock, "POST", "/patients")[0]!.body).toEqual({ full_name: "Ana Test", age: 41 });
  });
});
