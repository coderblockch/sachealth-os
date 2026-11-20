import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it } from "vitest";

import { PatientPicker } from "../components/PatientPicker";
import { callsTo, mockApi, renderWithProviders } from "../test/utils";

const all = Array.from({ length: 150 }, (_, i) => ({
  id: i + 1,
  full_name: i === 0 ? "Oldest Person" : `Patient ${i + 1}`,
  age: 50,
  created_at: "2026-11-20T04:00:00Z",
}));

function Harness() {
  const [value, setValue] = useState("");
  return (
    <>
      <label htmlFor="pick">Patient</label>
      <PatientPicker id="pick" value={value} onChange={setValue} />
      <output>selected:{value}</output>
    </>
  );
}

describe("PatientPicker", () => {
  it("reaches a patient outside the first page by searching the API", async () => {
    const fetchMock = mockApi({
      "GET /patients": ({ url }) => {
        const q = (url.searchParams.get("q") ?? "").toLowerCase();
        const limit = Number(url.searchParams.get("limit"));
        const newestFirst = [...all].reverse().filter((p) => p.full_name.toLowerCase().includes(q));
        return { json: { items: newestFirst.slice(0, limit), total: newestFirst.length, limit, offset: 0 } };
      },
    });
    renderWithProviders(<Harness />, { signedIn: true });
    await screen.findByRole("option", { name: /patient 150/i });
    expect(screen.queryByRole("option", { name: /oldest person/i })).not.toBeInTheDocument();
    expect(screen.getByText(/type a name to find others/i)).toBeInTheDocument();

    await userEvent.type(screen.getByRole("searchbox", { name: /search patients/i }), "oldest");
    await userEvent.selectOptions(screen.getByLabelText("Patient"), await screen.findByRole("option", { name: /oldest person/i }));
    expect(screen.getByText("selected:1")).toBeInTheDocument();
    expect(callsTo(fetchMock, "GET", "/patients").at(-1)!.params).toMatchObject({ q: "oldest", limit: "20" });
  });
});
