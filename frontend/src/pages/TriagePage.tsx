import { TriageForm } from "../components/TriageForm";
import { TriageHistory } from "../components/TriageHistory";

export function TriagePage() {
  return (
    <section aria-labelledby="triage-title">
      <h1 id="triage-title" className="page-title">
        Clinical triage
      </h1>
      <p className="mb-6 text-sm text-slate-400">
        Rule-based decision support. Each analysis is stored in the patient's history.
      </p>
      <div className="grid gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
        <TriageForm />
        <TriageHistory />
      </div>
    </section>
  );
}
