import { apiRequest } from "./client";
import type {
  Bed,
  BedStatus,
  CurrentUser,
  Page,
  Patient,
  PatientDetail,
  PatientFilters,
  Stats,
  TokenResponse,
  TriageCreate,
  TriageFilters,
  TriageRecord,
} from "./types";

// One function per backend endpoint. Components never call fetch directly.
export const api = {
  login: (email: string, password: string) =>
    apiRequest<TokenResponse>("/auth/login", { method: "POST", body: { email, password }, auth: false }),
  me: () => apiRequest<CurrentUser>("/auth/me"),

  stats: () => apiRequest<Stats>("/stats", { auth: false }),

  beds: (status?: BedStatus) => apiRequest<Bed[]>("/beds", { params: { status }, auth: false }),
  assignBed: (bedId: number, patientId: number) =>
    apiRequest<Bed>(`/beds/${bedId}/assign`, { method: "POST", body: { patient_id: patientId } }),
  dischargeBed: (bedId: number) => apiRequest<Bed>(`/beds/${bedId}/discharge`, { method: "POST" }),

  patients: (filters: PatientFilters) => apiRequest<Page<Patient>>("/patients", { params: { ...filters } }),
  patient: (id: number) => apiRequest<PatientDetail>(`/patients/${id}`),
  createPatient: (body: { full_name: string; age: number }) =>
    apiRequest<Patient>("/patients", { method: "POST", body }),
  deletePatient: (id: number) => apiRequest<void>(`/patients/${id}`, { method: "DELETE" }),

  triageHistory: (filters: TriageFilters) =>
    apiRequest<Page<TriageRecord>>("/triage", { params: { ...filters } }),
  createTriage: (body: TriageCreate) => apiRequest<TriageRecord>("/triage", { method: "POST", body }),
};
