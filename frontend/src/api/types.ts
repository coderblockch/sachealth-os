// Types mirror the FastAPI response models in backend/main.py.

export const BED_STATUSES = ["Available", "Occupied", "Pending_Discharge", "Cleaning"] as const;
export type BedStatus = (typeof BED_STATUSES)[number];

export type Priority = 1 | 2 | 3 | 4;

export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface TokenResponse {
  access_token: string;
  token_type: "bearer";
}

export interface CurrentUser {
  id: number;
  email: string;
  full_name: string;
}

export interface Bed {
  id: number;
  num: string;
  status: BedStatus;
  patient: string | null;
  patient_id: number | null;
  updated_at: string;
}

export interface Patient {
  id: number;
  full_name: string;
  age: number;
  created_at: string;
}

export interface TriageRecord {
  id: number;
  patient_id: number;
  age: number;
  oxygen_level: number;
  symptoms: string;
  priority: Priority;
  recommendation: string;
  urgency: string;
  created_by_id: number | null;
  created_at: string;
}

export interface PatientDetail extends Patient {
  current_bed: string | null;
  triage_history: TriageRecord[];
}

export interface Stats {
  beds_by_status: Record<BedStatus, number>;
  triage_by_priority: Record<"1" | "2" | "3" | "4", number>;
}

/** Body for POST /triage: exactly one of patient_id / patient_name. */
export type TriageCreate = {
  age: number;
  oxygen_level: number;
  symptoms: string;
} & ({ patient_id: number; patient_name?: never } | { patient_name: string; patient_id?: never });

export interface TriageFilters {
  priority?: Priority;
  patient_id?: number;
  since?: string;
  limit?: number;
  offset?: number;
}

export interface PatientFilters {
  q?: string;
  limit?: number;
  offset?: number;
}
