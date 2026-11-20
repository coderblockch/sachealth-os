import { NavLink, Outlet } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";

const links = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/triage", label: "Triage" },
  { to: "/patients", label: "Patients" },
  { to: "/beds", label: "Beds" },
];

export function Layout() {
  const { user, logout } = useAuth();
  return (
    <div className="min-h-screen">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:m-2 focus:rounded focus:bg-blue-600 focus:px-3 focus:py-1">
        Skip to content
      </a>
      <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-4 px-4 py-3">
          <span className="text-lg font-bold">
            <span aria-hidden>🏥</span> SacHealth <span className="text-blue-400">OS</span>
          </span>
          <nav aria-label="Main" className="order-3 flex w-full gap-1 overflow-x-auto sm:order-none sm:w-auto">
            {links.map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
                end={link.end}
                className={({ isActive }) =>
                  `rounded-lg px-3 py-1.5 text-sm font-medium ${isActive ? "bg-blue-600 text-white" : "text-slate-300 hover:bg-slate-800"}`
                }
              >
                {link.label}
              </NavLink>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-3 text-sm text-slate-400">
            <span className="hidden sm:inline">{user?.full_name || user?.email}</span>
            <button type="button" onClick={logout} className="btn-secondary">
              Sign out
            </button>
          </div>
        </div>
      </header>
      <main id="main" className="mx-auto max-w-6xl px-4 py-6">
        <Outlet />
      </main>
      <footer className="mx-auto max-w-6xl px-4 pb-6 text-xs text-slate-600">
        Educational prototype with fake data. Not for real clinical use.
      </footer>
    </div>
  );
}
