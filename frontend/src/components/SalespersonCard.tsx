// Manager Phase 4: a single salesperson "card" used by the team page,
// the assignment menu summary, and the advisor workspace hero.
//
// Accepts either the public payload (no contact info) or the admin
// payload (phone/email + bio). Renders contact details only when present.

import { Link } from "react-router-dom";
import { Mail, Phone, User } from "lucide-react";

import type { SalespersonAdmin, SalespersonPublic } from "@/lib/api";
import { cn } from "@/lib/utils";

interface Props {
  advisor: SalespersonAdmin | SalespersonPublic;
  /** Whether to render the "Open workspace" link to /dealer-ai-advisor/<slug>. */
  showWorkspaceLink?: boolean;
  /** Optional: show inactive marker when the advisor is deactivated. */
  showInactiveBadge?: boolean;
  className?: string;
}

function isAdminPayload(
  advisor: SalespersonAdmin | SalespersonPublic,
): advisor is SalespersonAdmin {
  return (
    "email" in advisor || "phone" in advisor || "bio" in advisor
  );
}

export default function SalespersonCard({
  advisor,
  showWorkspaceLink = true,
  showInactiveBadge = false,
  className,
}: Props) {
  const admin = isAdminPayload(advisor) ? advisor : null;
  const inactive = !advisor.is_active;
  return (
    <div
      className={cn(
        "card flex flex-col gap-3 p-4",
        inactive && "opacity-60",
        className,
      )}
    >
      <div className="flex items-start gap-3">
        {advisor.photo_url ? (
          <img
            src={advisor.photo_url}
            alt={`${advisor.name} headshot`}
            className="h-14 w-14 flex-none rounded-full border border-slate-200 object-cover"
            onError={(e) => {
              // Defensive: hide broken images instead of leaving blank squares.
              (e.target as HTMLImageElement).style.display = "none";
            }}
          />
        ) : (
          <div className="flex h-14 w-14 flex-none items-center justify-center rounded-full bg-slate-100 text-slate-400">
            <User className="h-6 w-6" />
          </div>
        )}
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-1.5">
            <div className="text-sm font-bold text-brand-ink">
              {advisor.name}
            </div>
            {showInactiveBadge && inactive ? (
              <span className="rounded-full border border-slate-300 bg-slate-100 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-slate-600">
                inactive
              </span>
            ) : null}
          </div>
          {advisor.title ? (
            <div className="text-xs text-slate-500">{advisor.title}</div>
          ) : null}
          {advisor.specialties.length > 0 ? (
            <div className="mt-1 flex flex-wrap gap-1">
              {advisor.specialties.slice(0, 4).map((s) => (
                <span
                  key={s}
                  className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-medium text-slate-700"
                >
                  {s}
                </span>
              ))}
            </div>
          ) : null}
        </div>
      </div>

      {admin ? (
        <div className="flex flex-col gap-1 text-xs text-slate-600">
          {admin.phone ? (
            <div className="flex items-center gap-2">
              <Phone className="h-3 w-3 text-slate-400" />
              <a
                href={`tel:${admin.phone}`}
                className="hover:text-brand-blue"
              >
                {admin.phone}
              </a>
            </div>
          ) : null}
          {admin.email ? (
            <div className="flex items-center gap-2">
              <Mail className="h-3 w-3 text-slate-400" />
              <a
                href={`mailto:${admin.email}`}
                className="hover:text-brand-blue"
              >
                {admin.email}
              </a>
            </div>
          ) : null}
          {admin.bio ? (
            <p className="mt-1 text-[11px] leading-snug text-slate-500">
              {admin.bio}
            </p>
          ) : null}
        </div>
      ) : null}

      {showWorkspaceLink && advisor.is_active ? (
        <Link
          to={`/dealer-ai-advisor/${advisor.slug}`}
          className="mt-auto inline-flex items-center justify-center rounded-md border border-brand-blue bg-white px-2.5 py-1 text-[11px] font-semibold text-brand-blue hover:bg-brand-blue hover:text-white"
        >
          Open workspace →
        </Link>
      ) : null}
    </div>
  );
}
