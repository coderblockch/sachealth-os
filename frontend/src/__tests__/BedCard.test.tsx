import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import type { Bed } from "../api/types";
import { BedCard } from "../components/BedCard";
import { callsTo, mockApi, renderWithProviders } from "../test/utils";

const bed = (overrides: Partial<Bed> = {}): Bed => ({
  id: 3, num: "103", status: "Available", patient: null, patient_id: null, updated_at: "2026-11-20T04:00:00Z", ...overrides,
});
const ana = { id: 5, full_name: "Ana Test", age: 40, created_at: "2026-11-20T04:00:00Z" };

describe("BedCard", () => {
  it("assigns a chosen patient to an available bed", async () => {
    const fetchMock = mockApi({
      "GET /patients": { items: [ana], total: 1, limit: 20, offset: 0 },
      "POST /beds/3/assign": bed({ status: "Occupied", patient: "Ana Test", patient_id: 5 }),
    });
    renderWithProviders(<BedCard bed={bed()} assignedIds={new Set()} />, { signedIn: true });
    const assign = screen.getByRole("button", { name: "Assign" });
    expect(assign).toBeDisabled();
    await screen.findByRole("option", { name: /ana test/i });
    await userEvent.selectOptions(screen.getByLabelText("Patient for bed 103"), "5");
    await userEvent.click(assign);
    await screen.findByRole("button", { name: "Assign" });
    expect(callsTo(fetchMock, "POST", "/beds/3/assign")[0]!.body).toEqual({ patient_id: 5 });
  });

  it("discharges an occupied bed and shows API conflicts", async () => {
    mockApi({ "POST /beds/1/discharge": () => ({ status: 409, json: { detail: "Bed is Cleaning, nobody to discharge" } }) });
    renderWithProviders(<BedCard bed={bed({ id: 1, num: "101", status: "Occupied", patient: "John Doe", patient_id: 1 })} assignedIds={new Set([1])} />, {
      signedIn: true,
    });
    expect(screen.getByText("John Doe")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Assign" })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Discharge bed 101" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("nobody to discharge");
  });
});
