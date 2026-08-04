// Milestone 27 · Increment 2 (SESSION_193) — chart-of-accounts picker.
//
// Renders a searchable single-select over the tenant's GLAccount list
// (sourced from the M27.1 GET /admin/accounting/gl-accounts/ endpoint
// via ``fetchGLAccounts`` — passed in as a prop; this component does
// not fetch). The filter matches both ``code`` and ``name``
// case-insensitively per M27.0 §5.b user direction so accountants can
// search either "1010" or "Cash" and land the same row.
//
// UI is built on the existing shadcn ``Input`` + Tailwind primitives
// rather than shadcn ``Command`` — the installed shadcn subset (see
// components/ui/) doesn't include Command/Popover, and CLAUDE.md
// frontend-stack notes forbid re-running ``npx shadcn init`` under
// the current v3+v4 bridge without confirmation. A plain filtered
// list is sufficient for the JE-create dialog's needs and adds no
// new UI primitives.

import { useMemo, useState } from "react";

import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import type { GLAccount } from "@/lib/accountingApi";


export interface GLAccountPickerProps {
  accounts: GLAccount[];
  value: number | null;
  onChange: (id: number | null) => void;
  disabled?: boolean;
  /** Accessible label id — the surrounding form supplies this so
   * screen readers announce the field label alongside the picker. */
  labelledBy?: string;
}


export function GLAccountPicker({
  accounts,
  value,
  onChange,
  disabled = false,
  labelledBy,
}: GLAccountPickerProps) {
  const [query, setQuery] = useState("");

  const filtered = useMemo(() => {
    const trimmed = query.trim().toLowerCase();
    if (!trimmed) return accounts;
    return accounts.filter((account) => {
      return (
        account.code.toLowerCase().includes(trimmed) ||
        account.name.toLowerCase().includes(trimmed)
      );
    });
  }, [accounts, query]);

  const selected = useMemo(
    () => accounts.find((account) => account.id === value) ?? null,
    [accounts, value],
  );

  return (
    <div className="flex flex-col gap-2" aria-labelledby={labelledBy}>
      {selected && (
        <div
          className="flex items-center justify-between gap-2 rounded-md border border-input bg-muted/30 px-3 py-2 text-sm"
          data-testid="gl-account-picker-selected"
        >
          <span className="tabular-nums">
            <span className="font-medium">{selected.code}</span>
            <span className="mx-1 text-muted-foreground">—</span>
            <span>{selected.name}</span>
          </span>
          <button
            type="button"
            className="text-xs text-muted-foreground underline"
            disabled={disabled}
            onClick={() => onChange(null)}
          >
            Change
          </button>
        </div>
      )}
      {!selected && (
        <>
          <Input
            type="search"
            role="searchbox"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search by code or name (e.g., 1010 or Cash)"
            disabled={disabled}
            aria-labelledby={labelledBy}
          />
          <ul
            className="max-h-48 overflow-y-auto rounded-md border border-input"
            role="listbox"
          >
            {filtered.length === 0 && (
              <li className="px-3 py-2 text-sm text-muted-foreground">
                No accounts match “{query}”.
              </li>
            )}
            {filtered.map((account) => (
              <li key={account.id} role="option" aria-selected="false">
                <button
                  type="button"
                  className={cn(
                    "flex w-full items-center justify-between gap-2 px-3 py-2 text-left text-sm hover:bg-accent hover:text-accent-foreground",
                    "focus:bg-accent focus:text-accent-foreground focus:outline-none",
                  )}
                  disabled={disabled}
                  onClick={() => onChange(account.id)}
                  data-testid={`gl-account-option-${account.code}`}
                >
                  <span className="tabular-nums">
                    <span className="font-medium">{account.code}</span>
                    <span className="mx-1 text-muted-foreground">—</span>
                    <span>{account.name}</span>
                  </span>
                  <span className="text-xs uppercase tracking-wide text-muted-foreground">
                    {account.type}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
