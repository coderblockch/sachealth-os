import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "./endpoints";
import type { BedStatus, PatientFilters, TriageCreate, TriageFilters } from "./types";

/** Central query keys so mutations can invalidate exactly what they change. */
export const queryKeys = {
  stats: ["stats"] as const,
  beds: (status?: BedStatus) => ["beds", status ?? "all"] as const,
  patients: (filters: PatientFilters) => ["patients", filters] as const,
  patient: (id: number) => ["patient", id] as const,
  triage: (filters: TriageFilters) => ["triage", filters] as const,
};

export const useStats = () => useQuery({ queryKey: queryKeys.stats, queryFn: api.stats });

export const useBeds = (status?: BedStatus) =>
  useQuery({ queryKey: queryKeys.beds(status), queryFn: () => api.beds(status) });

export const usePatients = (filters: PatientFilters) =>
  useQuery({
    queryKey: queryKeys.patients(filters),
    queryFn: () => api.patients(filters),
    placeholderData: keepPreviousData, // keep the old page visible while the next one loads
  });

export const usePatient = (id: number) =>
  useQuery({ queryKey: queryKeys.patient(id), queryFn: () => api.patient(id), enabled: Number.isFinite(id) });

export const useTriageHistory = (filters: TriageFilters) =>
  useQuery({
    queryKey: queryKeys.triage(filters),
    queryFn: () => api.triageHistory(filters),
    placeholderData: keepPreviousData,
  });

/** After any write, refresh every list that could show the changed data. */
function useInvalidateClinicalData() {
  const queryClient = useQueryClient();
  return () =>
    Promise.all(
      ["beds", "patients", "patient", "triage", "stats"].map((key) =>
        queryClient.invalidateQueries({ queryKey: [key] }),
      ),
    );
}

export function useCreateTriage() {
  const invalidate = useInvalidateClinicalData();
  return useMutation({ mutationFn: (body: TriageCreate) => api.createTriage(body), onSuccess: invalidate });
}

export function useCreatePatient() {
  const invalidate = useInvalidateClinicalData();
  return useMutation({ mutationFn: api.createPatient, onSuccess: invalidate });
}

export function useAssignBed() {
  const invalidate = useInvalidateClinicalData();
  return useMutation({
    mutationFn: ({ bedId, patientId }: { bedId: number; patientId: number }) => api.assignBed(bedId, patientId),
    onSuccess: invalidate,
  });
}

export function useDischargeBed() {
  const invalidate = useInvalidateClinicalData();
  return useMutation({ mutationFn: (bedId: number) => api.dischargeBed(bedId), onSuccess: invalidate });
}
