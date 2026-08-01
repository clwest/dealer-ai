// Milestone 3 · Increment 7 — per-finding photo gallery.
//
// Each finding owns its own gallery (per M3.7 spec: "do not create
// one global report gallery"). No reordering, no drag-and-drop, no
// caption editing after attach — those are explicit scope
// exclusions.
//
// Signed read URLs come from the M3.6A projection
// (``signed_read_url`` — regenerated fresh per response by the
// backend, so we never cache or persist them).
//
// Delete affordance renders only when ``canDelete=true`` (the
// parent report is a draft AND the caller has a write role). Server
// authorization remains authoritative — 409 on completed reports
// is caught here and surfaced as a specific message.

import { useState } from "react";
import { Trash2, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/authFetch";
import { deletePhoto, type ConditionPhoto } from "@/lib/api";

interface Props {
  stock: string;
  photos: ConditionPhoto[];
  canDelete: boolean;
  onDeleted: (publicId: string) => void;
}

function _formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function _formatDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function _humanizeDeleteError(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 409) {
      return "Report is complete — photos cannot be deleted.";
    }
    if (err.status === 502) {
      return "Storage provider unavailable. Photo was retained; try again shortly.";
    }
    if (err.status === 404) {
      return "Photo not found. Refresh the page.";
    }
    return `Server returned ${err.status}.`;
  }
  return "Delete failed. Check your connection.";
}

export function PhotoGallery({
  stock,
  photos,
  canDelete,
  onDeleted,
}: Props) {
  if (photos.length === 0) {
    return (
      <p className="text-xs text-muted-foreground italic">
        No photos attached yet.
      </p>
    );
  }

  return (
    <ul className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4">
      {photos.map((p) => (
        <PhotoTile
          key={p.public_id}
          stock={stock}
          photo={p}
          canDelete={canDelete}
          onDeleted={() => onDeleted(p.public_id)}
        />
      ))}
    </ul>
  );
}

function PhotoTile({
  stock,
  photo,
  canDelete,
  onDeleted,
}: {
  stock: string;
  photo: ConditionPhoto;
  canDelete: boolean;
  onDeleted: () => void;
}) {
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Detect the local-mode marker prefix. When the M3.4 storage
  // adapter is FileSystemStorage, ``signed_read_url`` is a marker
  // string, not a real URL. We can't render an <img> to a marker;
  // show a placeholder that clearly communicates the local-dev
  // state rather than silently rendering broken alt text.
  const isLocalDevReadUrl = photo.signed_read_url.startsWith(
    "local-dev-no-signature-read",
  );

  async function handleDelete() {
    setError(null);
    setDeleting(true);
    try {
      await deletePhoto(stock, photo.public_id);
      onDeleted();
    } catch (err) {
      setError(_humanizeDeleteError(err));
    } finally {
      setDeleting(false);
    }
  }

  return (
    <li className="flex flex-col gap-1.5 rounded-md border border-border bg-card p-2">
      {isLocalDevReadUrl ? (
        <div className="flex aspect-square items-center justify-center rounded bg-muted text-center text-[10px] text-muted-foreground">
          Local dev — no signed URL
        </div>
      ) : (
        <img
          src={photo.signed_read_url}
          alt={photo.caption || "Condition photo"}
          className="aspect-square w-full rounded object-cover"
          loading="lazy"
        />
      )}
      <div className="flex flex-col gap-0.5 text-[11px] text-muted-foreground">
        {photo.caption ? (
          <span className="line-clamp-2 font-medium text-foreground">
            {photo.caption}
          </span>
        ) : null}
        <span>
          {_formatBytes(photo.size_bytes)} · {_formatDate(photo.created_at)}
        </span>
        {photo.uploaded_by ? (
          <span>by {photo.uploaded_by}</span>
        ) : null}
      </div>
      {canDelete ? (
        <div className="flex flex-col gap-1">
          <Button
            type="button"
            size="sm"
            variant="ghost"
            className="h-7 w-full gap-1 text-[11px] text-muted-foreground hover:text-rose-700"
            disabled={deleting}
            onClick={handleDelete}
          >
            {deleting ? (
              <Loader2 className="h-3 w-3 animate-spin" aria-hidden="true" />
            ) : (
              <Trash2 className="h-3 w-3" aria-hidden="true" />
            )}
            Delete
          </Button>
          {error ? (
            <p role="alert" className="text-[10px] text-rose-700">
              {error}
            </p>
          ) : null}
        </div>
      ) : null}
    </li>
  );
}
