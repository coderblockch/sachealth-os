import { z } from "zod";

import type { TriageCreate } from "../api/types";

/** A numeric text input: "" means "missing" (z.coerce alone would turn "" into 0). */
export const integerField = (label: string, min: number, max: number, rangeMessage: string) =>
  z
    .string()
    .trim()
    .min(1, `${label} is required`)
    .pipe(z.coerce.number().int("Whole numbers only").min(min, rangeMessage).max(max, rangeMessage));

// Same limits as the API (TriageCreate in backend/main.py), checked before sending.
export const triageSchema = z
  .object({
    mode: z.enum(["new", "existing"]),
    patientName: z.string().trim().max(120, "Max 120 characters").optional(),
    patientId: z.string().optional(),
    age: integerField("Age", 0, 130, "Age must be 0–130"),
    oxygen: integerField("O₂ saturation", 0, 100, "O₂ must be 0–100"),
    symptoms: z.string().max(2000, "Max 2000 characters"),
  })
  .superRefine((values, ctx) => {
    if (values.mode === "new" && !values.patientName) {
      ctx.addIssue({ code: "custom", path: ["patientName"], message: "Patient name is required" });
    }
    if (values.mode === "existing" && !values.patientId) {
      ctx.addIssue({ code: "custom", path: ["patientId"], message: "Choose a patient" });
    }
  });

export type TriageFormValues = z.input<typeof triageSchema>;

export function toTriageRequest(values: z.output<typeof triageSchema>): TriageCreate {
  const common = { age: values.age, oxygen_level: values.oxygen, symptoms: values.symptoms.trim() };
  return values.mode === "existing"
    ? { ...common, patient_id: Number(values.patientId) }
    : { ...common, patient_name: values.patientName ?? "" };
}

