import { screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { RequireAuth } from "../auth/RequireAuth";
import { demoUser, mockApi, renderWithProviders } from "../test/utils";

const Secret = () => (
  <RequireAuth>
    <p>Secret page</p>
  </RequireAuth>
);

describe("RequireAuth", () => {
  it("redirects signed-out users to /login", async () => {
    mockApi({});
    renderWithProviders(<Secret />, { route: "/beds" });
    expect(await screen.findByText("Login screen")).toBeInTheDocument();
    expect(screen.queryByText("Secret page")).not.toBeInTheDocument();
  });

  it("renders the page once /auth/me confirms the stored token", async () => {
    mockApi({ "GET /auth/me": demoUser });
    renderWithProviders(<Secret />, { route: "/beds", signedIn: true });
    expect(screen.getByRole("status")).toHaveTextContent(/checking your session/i);
    expect(await screen.findByText("Secret page")).toBeInTheDocument();
  });

  it("logs out and redirects when the stored token is rejected", async () => {
    mockApi({ "GET /auth/me": () => ({ status: 401, json: { detail: "Not authenticated" } }) });
    renderWithProviders(<Secret />, { route: "/beds", signedIn: true });
    expect(await screen.findByText("Login screen")).toBeInTheDocument();
    await waitFor(() => expect(localStorage.getItem("sachealth.token")).toBeNull());
  });
});
