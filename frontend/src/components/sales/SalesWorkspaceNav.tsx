// TASK_doors-and-matrix-refresh Part B — shared 4-tab strip that
// makes /dealer-ai-sales/be-backs and /dealer-ai-sales/test-drives
// reachable via a click.
//
// The four /dealer-ai-sales/* pages were previously URL-only —
// nothing in the shell linked to any of them. Adding a shared tab
// strip on all four gives the be-backs and test-drives doors a
// "beside the existing sales links" home (per the task's placement
// column) and, incidentally, makes leads + follow-ups reachable
// too. The single entry point into the cluster is the "Sales
// workspace" button on the sidebar-reachable LeadsPage.
//
// Role gating stays server-side: each of the four pages already
// enforces its role at the backend. This component renders for
// everyone, matching the F&I / F&I Incoming nav pattern in
// App.tsx.

import { NavLink } from "react-router-dom";

import { cn } from "@/lib/utils";

interface SalesTab {
  to: string;
  label: string;
}

const TABS: SalesTab[] = [
  { to: "/dealer-ai-sales/leads", label: "Leads" },
  { to: "/dealer-ai-sales/follow-ups", label: "Follow-ups" },
  { to: "/dealer-ai-sales/be-backs", label: "Be-backs" },
  { to: "/dealer-ai-sales/test-drives", label: "Test drives" },
];

export function SalesWorkspaceNav() {
  return (
    <nav
      aria-label="Sales workspace"
      className="flex flex-wrap items-center gap-1 border-b border-border pb-2"
      data-testid="sales-workspace-nav"
    >
      {TABS.map((tab) => (
        <NavLink
          key={tab.to}
          to={tab.to}
          end
          className={({ isActive }) =>
            cn(
              "rounded-md px-3 py-1.5 text-sm font-medium transition",
              isActive
                ? "bg-primary/10 text-primary"
                : "text-muted-foreground hover:bg-muted hover:text-foreground",
            )
          }
        >
          {tab.label}
        </NavLink>
      ))}
    </nav>
  );
}
