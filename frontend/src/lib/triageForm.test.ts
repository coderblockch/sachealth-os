import { describe, expect, it } from "vitest";

import { toTriageRequest, triageSchema } from "./triageForm";

describe("triage form schema", () => {
  it("builds a new-patient request", () => {
    const values = triageSchema.parse({ mode: "new", patientName: "  Ana ", age: "72", oxygen: "93", symptoms: " cough " });
    expect(toTriageRequest(values)).toEqual({ patient_name: "Ana", age: 72, oxygen_level: 93, symptoms: "cough" });
  });

  it("builds an existing-patient request", () => {
    const values = triageSchema.parse({ mode: "existing", patientId: "7", age: "40", oxygen: "99", symptoms: "" });
    expect(toTriageRequest(values)).toEqual({ patient_id: 7, age: 40, oxygen_level: 99, symptoms: "" });
  });

  it("rejects out-of-range vitals and missing patient", () => {
    const result = triageSchema.safeParse({ mode: "new", patientName: " ", age: "200", oxygen: "101", symptoms: "" });
    expect(result.success).toBe(false);
    const fields = result.error!.issues.map((i) => i.path[0]);
    expect(fields).toEqual(expect.arrayContaining(["age", "oxygen", "patientName"]));
  });
});

describe("integer fields", () => {
  it("treats an empty age as missing instead of 0", () => {
    const result = triageSchema.safeParse({ mode: "new", patientName: "Ana", age: "", oxygen: "98", symptoms: "" });
    expect(result.success).toBe(false);
    expect(result.error!.issues[0]).toMatchObject({ path: ["age"], message: "Age is required" });
  });
});
