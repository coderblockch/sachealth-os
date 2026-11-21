import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { BedsPage } from "../pages/BedsPage";
import { mockApi, renderWithProviders } from "../test/utils";

const beds = [
  { id: 1, num: "101", status: "Occupied", patient: "Ana Test", patient_id: 5, updated_at: "2026-11-20T04:00:00Z" },
  { id: 3, num: "103", status: "Available", patient: null, patient_id: null, updated_at: "2026-11-20T04:00:00Z" },
];
const patients = [
  { id: 5, full_name: "Ana Test", age: 40, created_at: "2026-11-20T04:00:00Z" },
  { id: 6, full_name: "Ben Free", age: 52, created_at: "2026-11-20T04:00:00Z" },
];

describe("BedsPage", () => {
  it("never offers a patient who is in a bed hidden by the status filter", async () => {
    mockApi({ "GET /beds": beds, "GET /patients": { items: patients, total: 2, limit: 20, offset: 0 } });
    renderWithProviders(<BedsPage />, { signedIn: true, route: "/beds?status=Available" });

    const card = (await screen.findByRole("article", { name: "Bed 103" })) as HTMLElement;
    expect(screen.queryByRole("article", { name: "Bed 101" })).not.toBeInTheDocument();
    const select = within(card).getByLabelText("Patient for bed 103");
    expect(await within(select).findByRole("option", { name: /ben free/i })).toBeInTheDocument();
    expect(within(select).queryByRole("option", { name: /ana test/i })).not.toBeInTheDocument();
  });

  it("filters the board without asking the API again", async () => {
    const fetchMock = mockApi({ "GET /beds": beds, "GET /patients": { items: [], total: 0, limit: 20, offset: 0 } });
    renderWithProviders(<BedsPage />, { signedIn: true });
    expect(await screen.findByRole("article", { name: "Bed 101" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Occupied" }));
    expect(screen.queryByRole("article", { name: "Bed 103" })).not.toBeInTheDocument();
    expect(screen.getByRole("article", { name: "Bed 101" })).toBeInTheDocument();
    expect(fetchMock.mock.calls.filter(([url]) => String(url).includes("/beds"))).toHaveLength(1);
  });
});
