import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { TriageForm } from "../components/TriageForm";
import { callsTo, mockApi, renderWithProviders } from "../test/utils";

const emptyPage = { items: [], total: 0, limit: 100, offset: 0 };

describe("TriageForm", () => {
  it("submits a new patient's vitals and shows the CDSS result", async () => {
    const fetchMock = mockApi({
      "GET /patients": emptyPage,
      "POST /triage": ({ body }) => ({
        status: 201,
        json: { id: 9, patient_id: 4, priority: 2, recommendation: "Respiratory Unit", urgency: "High", ...(body as object) },
      }),
    });
    renderWithProviders(<TriageForm />, { signedIn: true });
    await userEvent.type(screen.getByLabelText(/patient name/i), "Maria Gomez");
    await userEvent.type(screen.getByLabelText(/^age$/i), "76");
    await userEvent.type(screen.getByLabelText(/o₂ saturation/i), "94");
    await userEvent.type(screen.getByLabelText(/symptoms/i), "Persistent cough");
    await userEvent.click(screen.getByRole("button", { name: /analyze/i }));

    const result = await screen.findByRole("status");
    expect(result).toHaveTextContent("Respiratory Unit");
    expect(result).toHaveTextContent("P2 · High");
    expect(screen.getByRole("link", { name: /view patient #4/i })).toHaveAttribute("href", "/patients/4");
    expect(callsTo(fetchMock, "POST", "/triage")[0]!.body).toEqual({
      patient_name: "Maria Gomez",
      age: 76,
      oxygen_level: 94,
      symptoms: "Persistent cough",
    });
  });

  it("blocks invalid vitals with accessible error messages", async () => {
    const fetchMock = mockApi({ "GET /patients": emptyPage });
    renderWithProviders(<TriageForm />, { signedIn: true });
    await userEvent.type(screen.getByLabelText(/patient name/i), "X");
    await userEvent.type(screen.getByLabelText(/^age$/i), "140");
    await userEvent.type(screen.getByLabelText(/o₂ saturation/i), "120");
    await userEvent.click(screen.getByRole("button", { name: /analyze/i }));
    expect(await screen.findByText("Age must be 0–130")).toBeInTheDocument();
    expect(screen.getByText("O₂ must be 0–100")).toBeInTheDocument();
    expect(callsTo(fetchMock, "POST", "/triage")).toHaveLength(0);
  });

  it("can triage an existing patient chosen from the list", async () => {
    const fetchMock = mockApi({
      "GET /patients": { ...emptyPage, total: 1, items: [{ id: 7, full_name: "John Doe", age: 64, created_at: "2026-11-20T00:00:00Z" }] },
      "POST /triage": { id: 1, patient_id: 7, priority: 1, recommendation: "ICU (Immediate)", urgency: "CRITICAL" },
    });
    renderWithProviders(<TriageForm />, { signedIn: true });
    await userEvent.click(screen.getByLabelText(/existing patient/i));
    await userEvent.selectOptions(await screen.findByLabelText(/^patient$/i), await screen.findByRole("option", { name: /john doe/i }));
    await userEvent.type(screen.getByLabelText(/^age$/i), "64");
    await userEvent.type(screen.getByLabelText(/o₂ saturation/i), "85");
    await userEvent.click(screen.getByRole("button", { name: /analyze/i }));
    expect(await screen.findByText("ICU (Immediate)")).toBeInTheDocument();
    expect(callsTo(fetchMock, "POST", "/triage")[0]!.body).toMatchObject({ patient_id: 7, oxygen_level: 85 });
  });
});
