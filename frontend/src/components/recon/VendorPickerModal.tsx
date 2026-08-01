// Milestone 4 · Increment 7 — vendor picker modal.
//
// Lazy-loads the vendor list on open (avoids fetching every time
// the parent renders). Filters client-side by name / slug. Emits
// the selected vendor's slug via onPick.
//
// Deactivated vendors are shown de-emphasized but still selectable
// — an operator may deliberately choose an inactive vendor if they
// are documenting an already-in-flight relationship.

import { useEffect, useMemo, useState } from "react";
import { Search } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { fetchVendors, type Vendor } from "@/lib/api";

export interface VendorPickerModalProps {
  open: boolean;
  onClose: () => void;
  onPick: (vendor: Vendor) => void;
}

export function VendorPickerModal({
  open,
  onClose,
  onPick,
}: VendorPickerModalProps) {
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    setError(null);
    fetchVendors()
      .then((res) => setVendors(res.vendors))
      .catch(() => setError("Failed to load vendors."))
      .finally(() => setLoading(false));
  }, [open]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return vendors;
    return vendors.filter(
      (v) =>
        v.name.toLowerCase().includes(q) || v.slug.toLowerCase().includes(q),
    );
  }, [vendors, query]);

  return (
    <Dialog open={open} onOpenChange={(v) => (!v ? onClose() : null)}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Select a vendor</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <div className="relative">
            <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search by name or slug"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="pl-8"
            />
          </div>
          {loading && (
            <div className="text-sm text-muted-foreground">Loading vendors…</div>
          )}
          {error && <div className="text-sm text-destructive">{error}</div>}
          <div className="max-h-72 space-y-1 overflow-y-auto">
            {filtered.map((v) => (
              <button
                key={v.slug}
                type="button"
                onClick={() => onPick(v)}
                className={cn(
                  "flex w-full items-center justify-between rounded border p-2 text-left hover:bg-muted",
                  !v.is_active && "opacity-60",
                )}
              >
                <div>
                  <div className="text-sm font-medium">{v.name}</div>
                  <div className="text-xs text-muted-foreground">
                    {v.slug}
                    {v.categories.length > 0 && (
                      <> · {v.categories.join(", ")}</>
                    )}
                  </div>
                </div>
                {!v.is_active && (
                  <Badge variant="outline" className="text-xs">
                    Inactive
                  </Badge>
                )}
              </button>
            ))}
            {!loading && filtered.length === 0 && (
              <div className="text-sm text-muted-foreground">
                No vendors match this search.
              </div>
            )}
          </div>
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
