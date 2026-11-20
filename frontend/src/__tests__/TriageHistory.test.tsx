import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { TriageHistory } from "../components/TriageHistory";
import { callsTo, mockApi, renderWithProviders } from "../test/utils";

const record = (id: number, priority: number) => ({
  id, patient_id: id, age: 40, oxygen_level: 95, symptoms: "", priority,
  recommendation: priority === 1 ? "ICU (Immediate)" : "Outpatient Clinic", urgency: "Low",
  created_by_id: 1, created_at: "2026-11-20T04:00:00Z",
});

describe("TriageHistory", () => {
  it("filters by priority through the API and keeps the filter in the URL", async () => {
    const fetchMock = mockApi({
      "GET /triage": ({ url }) => {
        const p = url.searchParams.get("priority");
        const items = p === "1" ? [record(1, 1)] : [record(1, 1), record(2, 4)];
        return { json: { items, total: items.length, limit: 10, offset: 0 } };
      },
    });
    renderWithProviders(<TriageHistory />, { signedIn: true });
    expect(await screen.findAllByRole("listitem")).toHaveLength(2);
    await userEvent.selectOptions(screen.getByLabelText(/priority/i), "1");
    await waitFor(() => expect(screen.getAllByRole("listitem")).toHaveLength(1));
    expect(screen.getByTestId("location")).toHaveTextContent("?priority=1");
    expect(callsTo(fetchMock, "GET", "/triage").at(-1)!.params).toMatchObject({ priority: "1", limit: "10" });
  });

  it("shows an empty state", async () => {
    mockApi({ "GET /triage": { items: [], total: 0, limit: 10, offset: 0 } });
    renderWithProviders(<TriageHistory />, { signedIn: true });
    expect(await screen.findByText("No triage records")).toBeInTheDocument();
  });
});
