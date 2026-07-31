// SESSION_022 — public dealership-site navigation.
//
// Lives outside the OS shell, used by the customer-facing
// `/`, `/showroom`, and `/assistant` routes. Mirrors the
// pattern Hudiburg + samsfreedomford.com use: a thin info
// strip (sales / service / hours) above a primary nav row
// with the dealer's logo, anchor links, and a single high-
// contrast "Talk to AI" CTA on the right.
//
// The "Talk to AI" CTA is intentionally the only filled
// button — assistant-first is the demo's headline message.

import { useEffect, useState } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";
import { Bot, Menu, MessageCircle, Phone, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { useBrand, type Brand } from "@/lib/brand";
import { cn } from "@/lib/utils";

const NAV_LINKS: { href: string; label: string }[] = [
  { href: "/showroom", label: "Showroom" },
  { href: "/#finance", label: "Finance" },
  { href: "/#trade-in", label: "Trade-In" },
  { href: "/#reviews", label: "Reviews" },
  { href: "/#about", label: "About" },
];

// Demo-only contact info, sourced from the dealer's public
// marketing site (samsfreedomford.com) on 2026-05-02. In a
// real install these would flow from the onboarding profile.
const DEMO_SALES_PHONE = "(918) 426-2031";

export default function SiteNav() {
  const brand = useBrand();
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();

  useEffect(() => {
    setMobileOpen(false);
  }, [location.pathname, location.hash]);

  return (
    <header className="sticky top-0 z-30 border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80">
      <InfoStrip />
      <div className="mx-auto flex w-full max-w-7xl items-center justify-between gap-4 px-4 py-3 sm:px-6 lg:px-8">
        <Link
          to="/"
          className="flex items-center gap-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50 rounded-md"
          aria-label={`${brand.dealershipName} home`}
        >
          <BrandMark brand={brand} />
          <div className="hidden flex-col leading-tight sm:flex">
            <span className="text-sm font-semibold tracking-tight text-foreground">
              {brand.dealershipName}
            </span>
            <span className="text-[11px] uppercase tracking-[0.16em] text-muted-foreground">
              {brand.storeLocation}
            </span>
          </div>
        </Link>

        <nav className="hidden items-center gap-1 lg:flex">
          {NAV_LINKS.map((link) => (
            <NavItem key={link.href} {...link} />
          ))}
        </nav>

        <div className="flex items-center gap-2">
          <a
            href={`tel:${DEMO_SALES_PHONE.replace(/\D/g, "")}`}
            className="hidden items-center gap-1.5 rounded-md border border-border px-2.5 py-1.5 text-xs font-medium text-foreground hover:bg-muted md:inline-flex"
          >
            <Phone className="h-3.5 w-3.5" />
            {DEMO_SALES_PHONE}
          </a>
          <Button
            asChild
            size="lg"
            className="h-10 gap-1.5 bg-ford-blue px-4 text-sm font-semibold text-white hover:bg-ford-accent"
          >
            <Link to="/assistant">
              <Bot className="h-4 w-4" />
              Talk to AI
            </Link>
          </Button>
          <Button
            type="button"
            variant="outline"
            size="icon"
            className="h-10 w-10 lg:hidden"
            aria-label="Open menu"
            onClick={() => setMobileOpen(true)}
          >
            <Menu className="h-5 w-5" />
          </Button>
        </div>
      </div>

      <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
        <SheetContent side="right" className="w-80 p-0" showCloseButton={false}>
          <SheetHeader className="flex-row items-center justify-between border-b border-border px-5 py-4">
            <div>
              <SheetTitle className="text-left text-base">
                {brand.dealershipName}
              </SheetTitle>
              <SheetDescription className="text-left text-xs">
                {brand.storeLocation}
              </SheetDescription>
            </div>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              aria-label="Close menu"
              onClick={() => setMobileOpen(false)}
            >
              <X className="h-5 w-5" />
            </Button>
          </SheetHeader>
          <div className="flex flex-col gap-1 px-3 py-4">
            {NAV_LINKS.map((link) => (
              <NavItem key={link.href} {...link} mobile />
            ))}
            <div className="my-3 border-t border-border" />
            <Button
              asChild
              size="lg"
              className="h-12 justify-start gap-2 bg-ford-blue text-white hover:bg-ford-accent"
            >
              <Link to="/assistant">
                <MessageCircle className="h-5 w-5" />
                Talk to AI Assistant
              </Link>
            </Button>
            <a
              href={`tel:${DEMO_SALES_PHONE.replace(/\D/g, "")}`}
              className="mt-2 flex items-center gap-2 rounded-md border border-border px-3 py-3 text-sm font-medium hover:bg-muted"
            >
              <Phone className="h-4 w-4" />
              Sales · {DEMO_SALES_PHONE}
            </a>
          </div>
        </SheetContent>
      </Sheet>
    </header>
  );
}

function InfoStrip() {
  const brand = useBrand();
  return (
    <div className="hidden bg-ford-ink text-[11px] text-white/80 md:block">
      <div className="mx-auto flex w-full max-w-7xl items-center justify-between gap-3 px-4 py-1.5 sm:px-6 lg:px-8">
        <div className="flex items-center gap-4">
          <span>Sales · Mon–Sat 8:30–7</span>
          <span className="hidden lg:inline">Service · Mon–Fri 7:30–5:30</span>
          <span className="hidden xl:inline">
            720 S George Nigh Expy · McAlester, OK
          </span>
        </div>
        <div className="flex items-center gap-3">
          <span className="hidden sm:inline">{brand.tagline}</span>
          <span className="inline-flex items-center gap-1.5">
            <span className="relative flex h-1.5 w-1.5">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-70" />
              <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-emerald-400" />
            </span>
            AI Assistant online
          </span>
        </div>
      </div>
    </div>
  );
}

function NavItem({
  href,
  label,
  mobile = false,
}: {
  href: string;
  label: string;
  mobile?: boolean;
}) {
  const isHash = href.startsWith("/#");
  const base = mobile
    ? "px-4 py-3 text-base font-medium rounded-md hover:bg-muted"
    : "px-3 py-1.5 text-sm font-medium rounded-md hover:bg-muted text-foreground/80 hover:text-foreground";

  if (isHash) {
    return (
      <a href={href} className={base}>
        {label}
      </a>
    );
  }
  return (
    <NavLink
      to={href}
      end
      className={({ isActive }) =>
        cn(base, isActive ? "bg-muted text-foreground" : "")
      }
    >
      {label}
    </NavLink>
  );
}

function BrandMark({ brand }: { brand: Brand }) {
  const [errored, setErrored] = useState(false);
  useEffect(() => {
    setErrored(false);
  }, [brand.logoUrl]);

  if (errored) {
    return (
      <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-ford-blue text-xs font-bold text-white">
        SF
      </span>
    );
  }
  return (
    <img
      src={brand.logoUrl}
      alt={brand.dealershipName}
      onError={() => setErrored(true)}
      className="h-11 w-auto select-none"
      draggable={false}
    />
  );
}
