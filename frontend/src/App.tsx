import { NavLink, Outlet } from "react-router-dom";
import {
  Bot,
  GraduationCap,
  LayoutDashboard,
  Settings,
  Users,
} from "lucide-react";
import type { ComponentType, SVGProps } from "react";

import { cn } from "@/lib/utils";

interface NavItem {
  to: string;
  label: string;
  icon: ComponentType<SVGProps<SVGSVGElement>>;
  end: boolean;
}

const NAV_ITEMS: NavItem[] = [
  { to: "/dealer-ai-overview", label: "Overview", icon: LayoutDashboard, end: false },
  { to: "/dealer-ai-demo", label: "Live Assistant", icon: Bot, end: false },
  { to: "/dealer-ai-manager-chat", label: "Coaching Mode", icon: GraduationCap, end: false },
  { to: "/dealer-ai-admin/team", label: "Team", icon: Users, end: false },
  { to: "/dealer-ai-onboarding", label: "Setup", icon: Settings, end: false },
];

export default function App() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="flex min-h-screen">
        <Sidebar />
        <div className="flex flex-1 flex-col">
          <TopBar />
          <main className="flex-1 px-6 py-6">
            <Outlet />
          </main>
        </div>
      </div>
    </div>
  );
}

function Sidebar() {
  return (
    <aside className="hidden w-60 shrink-0 flex-col border-r border-border bg-muted/40 sm:flex">
      <div className="flex items-center gap-3 border-b border-border px-5 py-5">
        <div className="flex h-9 w-9 items-center justify-center rounded-md bg-primary text-sm font-bold text-primary-foreground">
          FF
        </div>
        <div className="text-sm font-semibold tracking-tight text-foreground">
          Freedom Ford AI
        </div>
      </div>
      <nav className="flex flex-1 flex-col gap-0.5 p-3">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 border-l-2 px-3 py-2 text-sm font-medium transition",
                isActive
                  ? "border-primary bg-background text-primary"
                  : "border-transparent text-muted-foreground hover:bg-background hover:text-foreground",
              )
            }
          >
            <item.icon className="h-4 w-4" aria-hidden />
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>
      <div className="border-t border-border px-5 py-4 text-xs text-muted-foreground">
        Local · MVP
      </div>
    </aside>
  );
}

function TopBar() {
  return (
    <header className="flex h-14 items-center justify-between border-b border-border bg-background px-6">
      <div className="flex items-center gap-3">
        <span className="text-sm font-semibold tracking-tight text-foreground">
          Freedom Ford
        </span>
        <span className="hidden text-xs text-muted-foreground sm:inline">
          Oklahoma · Dealer OS
        </span>
      </div>
      <AIActiveIndicator />
    </header>
  );
}

function AIActiveIndicator() {
  return (
    <div className="flex items-center gap-2 rounded-md border border-border bg-background px-2.5 py-1">
      <span className="relative flex h-2 w-2">
        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-500 opacity-60" />
        <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
      </span>
      <span className="text-xs font-medium text-foreground">AI Active</span>
    </div>
  );
}
