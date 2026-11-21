import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { LoginPage } from "../pages/LoginPage";
import { demoUser, fakeToken, mockApi, renderWithProviders } from "../test/utils";

describe("LoginPage", () => {
  it("validates the form before calling the API", async () => {
    const fetchMock = mockApi({});
    renderWithProviders(<LoginPage />, { route: "/signin" });
    await userEvent.type(screen.getByLabelText(/email/i), "not-an-email");
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));
    expect(await screen.findByText("Enter a valid email")).toBeInTheDocument();
    expect(screen.getByText("Password is required")).toBeInTheDocument();
    expect(screen.getByLabelText(/email/i)).toHaveAttribute("aria-invalid", "true");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("signs in, stores the token and returns to the requested page", async () => {
    const token = fakeToken();
    mockApi({ "POST /auth/login": { access_token: token, token_type: "bearer" }, "GET /auth/me": demoUser });
    renderWithProviders(<LoginPage />, { route: "/signin" });
    await userEvent.type(screen.getByLabelText(/email/i), "demo@sachealth.dev");
    await userEvent.type(screen.getByLabelText(/password/i), "sachealth-demo");
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));
    await waitFor(() => expect(screen.getByTestId("location")).toHaveTextContent(/^\/$/));
    expect(localStorage.getItem("sachealth.token")).toBe(token);
  });

  it("shows the server error for wrong credentials", async () => {
    mockApi({ "POST /auth/login": () => ({ status: 401, json: { detail: "Invalid email or password" } }) });
    renderWithProviders(<LoginPage />, { route: "/signin" });
    await userEvent.type(screen.getByLabelText(/email/i), "demo@sachealth.dev");
    await userEvent.type(screen.getByLabelText(/password/i), "wrong");
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Invalid email or password");
  });
});
