import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { DashboardPage } from "../pages/DashboardPage";
import { mockApi, renderWithProviders } from "../test/utils";

const stats = {
  beds_by_status: { Available: 2, Occupied: 4, Pending_Discharge: 2, Cleaning: 2 },
  triage_by_priority: { "1": 3, "2": 1, "3": 0, "4": 6 },
};

describe("DashboardPage", () => {
  it("shows stat cards and scales the bars to the data", async () => {
    mockApi({ "GET /stats": stats });
    renderWithProviders(<DashboardPage />);
    expect(await screen.findByText("60%")).toBeInTheDocument(); // (4 + 2) / 10 beds
    expect(screen.getByText("of 10 beds")).toBeInTheDocument();
    expect(screen.getByTestId("bar-Occupied")).toHaveStyle({ width: "100%" });
    expect(screen.getByTestId("bar-Available")).toHaveStyle({ width: "50%" });
    expect(screen.getByTestId("bar-P4 Low")).toHaveStyle({ width: "100%" });
  });

  it("shows an error with a working retry button", async () => {
    let calls = 0;
    mockApi({ "GET /stats": () => (++calls === 1 ? { status: 500, json: { detail: "Database down" } } : { json: stats }) });
    renderWithProviders(<DashboardPage />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Database down");
    await userEvent.click(screen.getByRole("button", { name: /try again/i }));
    expect(await screen.findByText("60%")).toBeInTheDocument();
  });
});
