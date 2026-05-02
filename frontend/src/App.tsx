import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import {
  Bot,
  Car,
  GraduationCap,
  LayoutDashboard,
  Menu,
  Settings,
  Users,
  UserSquare,
} from "lucide-react";
import type { ComponentType, SVGProps } from "react";

import { Button } from "@/components/ui/button";
import PublicPreviewDialog from "@/components/PublicPreviewDialog";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { useBrand, type Brand } from "@/lib/brand";
import { cn } from "@/lib/utils";

interface NavItem {
  to: string;
  label: string;
  icon: ComponentType<SVGProps<SVGSVGElement>>;
  end: boolean;
}

const NAV_ITEMS: NavItem[] = [
  { to: "/dealer-ai-overview", label: "Overview", icon: LayoutDashboard, end: false },
  { to: "/dealer-ai-live-assistant", label: "Live Assistant", icon: Bot, end: false },
  { to: "/dealer-ai-inventory", label: "Inventory", icon: Car, end: false },
  { to: "/dealer-ai-leads", label: "Leads", icon: UserSquare, end: false },
  { to: "/dealer-ai-manager-chat", label: "Coaching Mode", icon: GraduationCap, end: false },
  { to: "/dealer-ai-admin/team", label: "Team", icon: Users, end: false },
  { to: "/dealer-ai-onboarding", label: "Setup", icon: Settings, end: false },
];

// Real dealer logo, captured from samsfreedomford.com on 2026-05-02 and
// stored locally so the demo doesn't break when the dealer's CDN
// rotates. The logo asset is intentionally NOT keyed off
// onboarding-profile values — that's a brand-team upload, not a
// derivable string. See SESSION_018 handoff for the rationale.
const LOGO_SRC = "/branding/sams-freedom-ford-logo.jpg";
const PRODUCT_LABEL = "Dealer OS";

export default function App() {
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const location = useLocation();
  const brand = useBrand();

  // Close the mobile drawer whenever the route changes — clicking a
  // nav link inside the Sheet should land the user on the new page
  // without leaving the drawer floating open.
  useEffect(() => {
    setMobileNavOpen(false);
  }, [location.pathname]);

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="flex min-h-screen">
        <DesktopSidebar brand={brand} />
        <div className="flex flex-1 flex-col">
          <TopBar
            brand={brand}
            onOpenMobileNav={() => setMobileNavOpen(true)}
          />
          <main className="flex-1 px-4 py-6 sm:px-6">
            <Outlet />
          </main>
        </div>
      </div>

      <Sheet open={mobileNavOpen} onOpenChange={setMobileNavOpen}>
        <SheetContent
          side="left"
          className="w-64 bg-background p-0"
          showCloseButton
        >
          <SheetHeader className="border-b border-border">
            {/* SheetTitle is required for radix accessibility; render it
                visually hidden and let <BrandHeader /> handle the actual
                visual brand block. */}
            <SheetTitle className="sr-only">
              {brand.displayName} — {PRODUCT_LABEL}
            </SheetTitle>
            <SheetDescription className="sr-only">
              Primary navigation for the {PRODUCT_LABEL}.
            </SheetDescription>
            <BrandHeader brand={brand} compact />
          </SheetHeader>
          <NavList />
        </SheetContent>
      </Sheet>
    </div>
  );
}

function DesktopSidebar({ brand }: { brand: Brand }) {
  return (
    <aside className="hidden w-60 shrink-0 flex-col border-r border-border bg-muted/40 sm:flex">
      <BrandHeader brand={brand} />
      <NavList />
      <div className="border-t border-border px-5 py-4 text-[11px] italic text-muted-foreground">
        {brand.tagline}
      </div>
    </aside>
  );
}

/** Branded header block shared between desktop sidebar + mobile drawer.
 *  Renders the dealer's real logo with a graceful text fallback if the
 *  asset is missing. The product label ("Dealer OS") sits beneath as
 *  small caps so it never competes with the brand. */
function BrandHeader({
  brand,
  compact = false,
}: {
  brand: Brand;
  compact?: boolean;
}) {
  const [logoError, setLogoError] = useState(false);
  const padding = compact ? "px-4 py-3" : "px-5 py-4";
  const logoHeight = compact ? "h-9" : "h-11";

  return (
    <div className={cn("flex flex-col gap-1.5 border-b border-border", padding)}>
      <div className="flex items-center">
        {logoError ? (
          <BrandTextFallback brand={brand} />
        ) : (
          <img
            src={LOGO_SRC}
            alt={brand.displayName}
            onError={() => setLogoError(true)}
            className={cn(logoHeight, "w-auto select-none")}
            draggable={false}
          />
        )}
      </div>
      <div className="flex items-center gap-1.5 text-[10.5px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
        <span>{PRODUCT_LABEL}</span>
      </div>
    </div>
  );
}

function BrandTextFallback({ brand }: { brand: Brand }) {
  return (
    <div className="flex flex-col leading-tight">
      <span className="text-sm font-semibold tracking-tight text-foreground">
        {brand.dealershipName}
      </span>
      <span className="text-xs text-muted-foreground">
        {brand.storeLocation}
      </span>
    </div>
  );
}

function NavList() {
  return (
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
  );
}

function TopBar({
  brand,
  onOpenMobileNav,
}: {
  brand: Brand;
  onOpenMobileNav: () => void;
}) {
  return (
    <header className="flex h-14 items-center justify-between border-b border-border bg-background px-4 sm:px-6">
      <div className="flex items-center gap-2 sm:gap-3">
        <Button
          type="button"
          variant="ghost"
          size="icon-sm"
          className="sm:hidden"
          aria-label="Open navigation"
          onClick={onOpenMobileNav}
        >
          <Menu className="h-4 w-4" />
        </Button>
        <span className="text-sm font-semibold tracking-tight text-foreground">
          {brand.topbarName}
        </span>
        <span className="text-xs text-muted-foreground">
          · {brand.storeLocation}
        </span>
      </div>
      <div className="flex items-center gap-2 sm:gap-3">
        <PublicPreviewDialog />
        <AIActiveIndicator />
      </div>
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
