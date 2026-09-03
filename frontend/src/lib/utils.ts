import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatCurrency(
  value: number | string | null | undefined,
  options: Intl.NumberFormatOptions = {},
) {
  if (value === null || value === undefined || value === "") return "";
  const n = typeof value === "string" ? Number(value) : value;
  if (Number.isNaN(n)) return "";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
    ...options,
  }).format(n);
}

// SESSION_229 Part 3 — the recon page and the ledger page were
// formatting money two different ways one click apart. This is the
// ledger's string-manipulation formatter, promoted to a shared
// helper so callers do not parse through Number for arithmetic —
// the backend already sends fixed two-decimal-place strings, we
// just add a thousands separator + dollar sign for display.
export function formatMoney(value: string | null | undefined): string {
  if (value === null || value === undefined || value === "") return "$0.00";
  const negative = value.startsWith("-");
  const bare = negative ? value.slice(1) : value;
  const [whole = "0", frac = "00"] = bare.split(".");
  const withCommas = whole.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  const fracPadded = frac.length >= 2 ? frac.slice(0, 2) : frac.padEnd(2, "0");
  return `${negative ? "\u2212" : ""}$${withCommas}.${fracPadded}`;
}
