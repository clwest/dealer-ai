import { NavLink, Outlet } from "react-router-dom";

import { cn } from "@/lib/utils";

const NAV_LINKS = [
  { to: "/dealer-ai-demo", label: "Customer demo", end: false },
  // `end` makes this match only the exact dashboard path so it doesn't
  // also light up on `/dealer-ai-admin/team`.
  { to: "/dealer-ai-admin", label: "Manager dashboard", end: true },
  { to: "/dealer-ai-admin/team", label: "Sales team", end: false },
];

export default function App() {
  return (
    <div className="min-h-screen bg-ford-mist">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-ford-blue text-sm font-bold text-white">
                FF
              </div>
              <div>
                <div className="text-sm font-bold tracking-tight text-ford-ink">
                  Freedom Ford
                </div>
                <div className="text-xs text-slate-500">AI Concierge — MVP</div>
              </div>
            </div>
            <nav className="hidden gap-1 sm:flex">
              {NAV_LINKS.map((link) => (
                <NavLink
                  key={link.to}
                  to={link.to}
                  end={link.end}
                  className={({ isActive }) =>
                    cn(
                      "rounded-md px-3 py-1.5 text-sm font-medium transition",
                      isActive
                        ? "bg-ford-blue text-white"
                        : "text-slate-600 hover:bg-slate-100",
                    )
                  }
                >
                  {link.label}
                </NavLink>
              ))}
            </nav>
          </div>
          <div className="hidden items-center gap-3 sm:flex">
            <span className="rounded-full border border-amber-200 bg-amber-50 px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-amber-700">
              Demo data
            </span>
            <span className="text-xs text-slate-500">Oklahoma</span>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-8">
        <Outlet />
      </main>
    </div>
  );
}
