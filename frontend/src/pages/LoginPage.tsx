import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { z } from "zod";

import { useAuth } from "../auth/AuthContext";
import { FormField } from "../components/FormField";

const schema = z.object({
  email: z.string().trim().min(1, "Email is required").email("Enter a valid email"),
  password: z.string().min(1, "Password is required"),
});
type LoginValues = z.infer<typeof schema>;

export function LoginPage() {
  const { login, user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: string } | null)?.from ?? "/";
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginValues>({ resolver: zodResolver(schema) });

  if (user) return <Navigate to={from} replace />;

  const onSubmit = handleSubmit(async ({ email, password }) => {
    setServerError(null);
    try {
      await login(email, password);
      navigate(from, { replace: true });
    } catch (error) {
      setServerError(error instanceof Error ? error.message : "Sign in failed");
    }
  });

  return (
    <main className="flex min-h-screen items-center justify-center px-4">
      <div className="card w-full max-w-md">
        <h1 className="page-title">
          <span aria-hidden>🏥</span> SacHealth <span className="text-blue-400">OS</span>
        </h1>
        <p className="mb-6 text-sm text-slate-400">Staff sign in for triage and bed management.</p>
        <form onSubmit={onSubmit} noValidate className="flex flex-col gap-4">
          <FormField label="Email" error={errors.email?.message}>
            <input type="email" autoComplete="username" className="input" {...register("email")} />
          </FormField>
          <FormField label="Password" error={errors.password?.message}>
            <input type="password" autoComplete="current-password" className="input" {...register("password")} />
          </FormField>
          {serverError && (
            <p role="alert" className="rounded-lg bg-red-500/10 p-3 text-sm text-red-200">
              {serverError}
            </p>
          )}
          <button type="submit" className="btn-primary" disabled={isSubmitting}>
            {isSubmitting ? "Signing in…" : "Sign in"}
          </button>
        </form>
        <p className="mt-6 rounded-lg bg-slate-800/60 p-3 text-xs text-slate-400">
          Demo account (fake data): <code className="text-slate-200">demo@sachealth.dev</code> /{" "}
          <code className="text-slate-200">sachealth-demo</code>
        </p>
      </div>
    </main>
  );
}
