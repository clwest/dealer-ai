// SESSION_022 — public dealership-site footer.
//
// Mirrors the column structure both reference sites use
// (Shop / Finance / About / Visit), preserves a thin
// "Operator OS" link so demo flows can hop into the kit's
// operator surface without a separate URL bookmark, and
// keeps a brand-aware credit line tying the AI experience
// back to the kit.

import { Link } from "react-router-dom";
import { Bot, MapPin, Phone } from "lucide-react";

import { PRODUCT } from "@/config/defaultDealer";
import { useBrand, useDealerProfile } from "@/lib/brand";

const COLUMNS: {
  heading: string;
  links: { label: string; to: string; external?: boolean }[];
}[] = [
  {
    heading: "Shop",
    links: [
      { label: "Showroom", to: "/showroom" },
      { label: "Talk to AI", to: "/assistant" },
      { label: "By model", to: "/showroom#models" },
      { label: "Pre-owned", to: "/showroom#used" },
    ],
  },
  {
    heading: "Finance",
    links: [
      { label: "Get pre-qualified", to: "/#finance" },
      { label: "Trade-in value", to: "/#trade-in" },
      { label: "Payment estimator", to: "/assistant?intent=payment" },
    ],
  },
  {
    heading: "About",
    links: [
      { label: "Why our AI", to: "/#trust" },
      { label: "Reviews", to: "/#reviews" },
      { label: "Visit us", to: "/#about" },
    ],
  },
];

export default function SiteFooter() {
  const brand = useBrand();
  const profile = useDealerProfile();
  const isFranchise = profile.dealerType === "franchise";
  const year = new Date().getFullYear();

  return (
    <footer className="border-t border-border bg-brand-ink text-white">
      <div className="mx-auto w-full max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
        <div className="grid gap-10 md:grid-cols-2 lg:grid-cols-4">
          <div className="space-y-3">
            <div className="text-base font-semibold tracking-tight">
              {brand.dealershipName}
            </div>
            <div className="text-sm text-white/70">
              {brand.tagline}
            </div>
            {brand.storeLocation && (
              <div className="flex items-center gap-2 text-sm text-white/80">
                <MapPin className="h-4 w-4 text-brand-accent" />
                <span>{brand.storeLocation}</span>
              </div>
            )}
            <div className="flex flex-col gap-1.5 text-sm">
              {brand.salesPhone && (
                <a
                  href={`tel:${brand.salesPhone.replace(/\D/g, "")}`}
                  className="flex items-center gap-2 text-white/80 hover:text-white"
                >
                  <Phone className="h-4 w-4 text-brand-accent" />
                  Sales · {brand.salesPhone}
                </a>
              )}
              {/* Service line is franchise-only — the Copper Canyon
                  indie persona (and any DEALER_AI_DEALER_TYPE=
                  independent config) has no service department.
                  Franchise dealers should ship a real service phone
                  from the profile once the schema has one; falls back
                  to the sales phone in the meantime rather than
                  hardcoding a McAlester number nobody at this
                  dealership answers. */}
              {isFranchise && brand.salesPhone && (
                <a
                  href={`tel:${brand.salesPhone.replace(/\D/g, "")}`}
                  className="flex items-center gap-2 text-white/80 hover:text-white"
                >
                  <Phone className="h-4 w-4 text-brand-accent" />
                  Service · {brand.salesPhone}
                </a>
              )}
            </div>
          </div>

          {COLUMNS.map((col) => (
            <div key={col.heading} className="space-y-3">
              <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-white/60">
                {col.heading}
              </div>
              <ul className="space-y-2 text-sm text-white/80">
                {col.links.map((link) => (
                  <li key={link.label}>
                    {link.to.startsWith("/#") ? (
                      <a href={link.to} className="hover:text-white">
                        {link.label}
                      </a>
                    ) : (
                      <Link to={link.to} className="hover:text-white">
                        {link.label}
                      </Link>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-10 flex flex-col gap-4 border-t border-white/10 pt-6 text-xs text-white/60 md:flex-row md:items-center md:justify-between">
          <div>
            © {year} {brand.dealershipName}. All rights reserved.
            {" "}Estimates and any vehicle availability shown are for demo
            purposes — confirm in person or by calling.
          </div>
          <div className="flex items-center gap-4">
            <span className="inline-flex items-center gap-1.5">
              <Bot className="h-3.5 w-3.5 text-brand-accent" />
              Powered by {PRODUCT.productName} · {PRODUCT.productSubtitle}
            </span>
            <Link
              to="/dealer-ai-overview"
              className="rounded-md border border-white/20 px-2.5 py-1 hover:border-white/40 hover:text-white"
            >
              Operator OS
            </Link>
          </div>
        </div>
      </div>
    </footer>
  );
}
