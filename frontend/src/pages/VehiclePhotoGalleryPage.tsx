// Milestone 6 · Increment 5 (SESSION_086) — operator photo gallery
// page. Consumes the six M6.5 photo admin endpoints.
//
// URL: /dealer-ai-inventory/:stock/photos
//
// Role gating (per §5.f SESSION_075 refined): write affordances
// (upload / reorder / set-primary / delete / restore) are gated to
// recon_manager / sales_manager / dealer_owner. Per-photo tenant
// isolation is enforced at the M6.2 service layer.
//
// UX shape: three panels — active gallery (grid), upload form,
// deleted panel (restore affordances).

import { useCallback, useEffect, useMemo, useState } from "react";
import { ArrowLeft, ImageOff, Loader2, Star, Trash2, Undo2 } from "lucide-react";
import { Link, useParams } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/lib/AuthContext";
import {
  ApiError,
  ForbiddenError,
  UnauthenticatedError,
} from "@/lib/authFetch";
import {
  fetchVehiclePhotos,
  markDeletedVehiclePhoto,
  restoreVehiclePhoto,
  setPrimaryVehiclePhoto,
  uploadVehiclePhoto,
  type VehiclePhotoDTO,
} from "@/lib/api";

const WRITE_ROLES = ["recon_manager", "sales_manager", "dealer_owner"];

function humanizeError(err: unknown): string {
  if (err instanceof UnauthenticatedError) {
    return "Your session expired. Please sign in again.";
  }
  if (err instanceof ForbiddenError) {
    return "You don't have permission to manage photos for this vehicle.";
  }
  if (err instanceof ApiError) {
    if (err.status === 404) {
      return "Vehicle or photo not found (or belongs to another dealership).";
    }
    if (err.status === 409) {
      return err.message || "Operation refused (already-deleted or state conflict).";
    }
    if (err.status === 415) {
      return err.message || "Unsupported image type — JPEG, PNG, or WebP only.";
    }
    if (err.status === 502) {
      return "Photo storage temporarily unavailable. Retry shortly.";
    }
    return err.message || `Request failed (HTTP ${err.status}).`;
  }
  return "Photo operation failed.";
}

async function readImageDimensions(file: File): Promise<{
  width: number;
  height: number;
}> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => {
      URL.revokeObjectURL(url);
      resolve({ width: img.naturalWidth, height: img.naturalHeight });
    };
    img.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error("Could not read image dimensions."));
    };
    img.src = url;
  });
}

function PhotoThumbnail({ photo }: { photo: VehiclePhotoDTO }) {
  const isLocalMarker = photo.read_url.startsWith("local-dev-");
  if (!photo.read_url || isLocalMarker) {
    return (
      <div className="flex h-32 w-full items-center justify-center rounded-md border border-dashed border-slate-300 bg-slate-50 text-xs text-muted-foreground">
        <ImageOff className="mr-1 h-4 w-4" />
        {isLocalMarker ? "local-dev" : "no preview"}
      </div>
    );
  }
  return (
    <img
      src={photo.read_url}
      alt={photo.caption || `Photo ${photo.public_id}`}
      className="h-32 w-full rounded-md object-cover"
    />
  );
}

export default function VehiclePhotoGalleryPage() {
  const { stock } = useParams();
  const { hasRole } = useAuth();
  const [photos, setPhotos] = useState<VehiclePhotoDTO[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionInFlight, setActionInFlight] = useState(false);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadCaption, setUploadCaption] = useState("");

  const canWrite = useMemo(() => hasRole(...WRITE_ROLES), [hasRole]);

  const refetch = useCallback(async () => {
    if (!stock) return;
    setLoading(true);
    setError(null);
    try {
      const data = await fetchVehiclePhotos(stock);
      setPhotos(data.photos);
    } catch (err) {
      setError(humanizeError(err));
    } finally {
      setLoading(false);
    }
  }, [stock]);

  useEffect(() => {
    refetch();
  }, [refetch]);

  const activePhotos = photos.filter((p) => p.marked_deleted_at === null);
  const deletedPhotos = photos.filter((p) => p.marked_deleted_at !== null);

  async function handleUpload() {
    if (!stock || !uploadFile) return;
    setActionError(null);
    setActionInFlight(true);
    try {
      const dims = await readImageDimensions(uploadFile);
      await uploadVehiclePhoto(stock, {
        file: uploadFile,
        width_px: dims.width,
        height_px: dims.height,
        caption: uploadCaption,
      });
      setUploadFile(null);
      setUploadCaption("");
      await refetch();
    } catch (err) {
      setActionError(humanizeError(err));
    } finally {
      setActionInFlight(false);
    }
  }

  async function handleSetPrimary(publicId: string) {
    setActionError(null);
    setActionInFlight(true);
    try {
      await setPrimaryVehiclePhoto(publicId);
      await refetch();
    } catch (err) {
      setActionError(humanizeError(err));
    } finally {
      setActionInFlight(false);
    }
  }

  async function handleDelete(publicId: string) {
    setActionError(null);
    setActionInFlight(true);
    try {
      await markDeletedVehiclePhoto(publicId);
      await refetch();
    } catch (err) {
      setActionError(humanizeError(err));
    } finally {
      setActionInFlight(false);
    }
  }

  async function handleRestore(publicId: string) {
    setActionError(null);
    setActionInFlight(true);
    try {
      await restoreVehiclePhoto(publicId);
      await refetch();
    } catch (err) {
      setActionError(humanizeError(err));
    } finally {
      setActionInFlight(false);
    }
  }

  return (
    <div className="mx-auto max-w-5xl space-y-4 px-4 py-6">
      <div className="flex items-center justify-between">
        <Link
          to="/dealer-ai-inventory"
          className="text-sm text-slate-600 hover:underline"
        >
          <ArrowLeft className="mr-1 inline h-4 w-4" />
          Back to inventory
        </Link>
        <h1 className="text-xl font-semibold">Photos · #{stock}</h1>
      </div>

      {loading && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading photos…
        </div>
      )}

      {error && (
        <div className="rounded-md border border-red-300 bg-red-50 p-3 text-sm text-red-800">
          {error}
        </div>
      )}

      {actionError && (
        <div className="rounded-md border border-red-300 bg-red-50 p-3 text-sm text-red-800">
          {actionError}
        </div>
      )}

      {!loading && !error && (
        <>
          <Card>
            <CardHeader>
              <CardTitle>
                Active gallery ({activePhotos.length})
              </CardTitle>
            </CardHeader>
            <CardContent>
              {activePhotos.length === 0 ? (
                <p className="italic text-muted-foreground text-sm">
                  No photos yet. Upload one below.
                </p>
              ) : (
                <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                  {activePhotos.map((photo) => (
                    <div
                      key={photo.public_id}
                      className="space-y-2 rounded-md border p-2"
                    >
                      <PhotoThumbnail photo={photo} />
                      <div className="text-xs text-muted-foreground">
                        {photo.width_px}×{photo.height_px}px
                        {photo.is_primary && (
                          <span className="ml-1 rounded bg-amber-100 px-1 text-amber-800">
                            primary
                          </span>
                        )}
                      </div>
                      {canWrite && (
                        <div className="flex flex-wrap gap-1">
                          {!photo.is_primary && (
                            <Button
                              variant="outline"
                              size="sm"
                              disabled={actionInFlight}
                              onClick={() => handleSetPrimary(photo.public_id)}
                            >
                              <Star className="mr-1 h-3 w-3" />
                              Set primary
                            </Button>
                          )}
                          <Button
                            variant="outline"
                            size="sm"
                            disabled={actionInFlight}
                            onClick={() => handleDelete(photo.public_id)}
                          >
                            <Trash2 className="mr-1 h-3 w-3" />
                            Delete
                          </Button>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {canWrite && (
            <Card>
              <CardHeader>
                <CardTitle>Upload a photo</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <input
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  onChange={(e) => setUploadFile(e.target.files?.[0] ?? null)}
                  className="text-sm"
                />
                <input
                  type="text"
                  placeholder="Caption (optional)"
                  value={uploadCaption}
                  onChange={(e) => setUploadCaption(e.target.value)}
                  className="w-full rounded-md border border-slate-300 px-2 py-1 text-sm"
                />
                <Button
                  onClick={handleUpload}
                  disabled={!uploadFile || actionInFlight}
                >
                  {actionInFlight ? "Uploading…" : "Upload"}
                </Button>
                <p className="text-xs text-muted-foreground">
                  JPEG / PNG / WebP. Listing-ready = ≥1024×768 (SESSION_083 §3).
                </p>
              </CardContent>
            </Card>
          )}

          {deletedPhotos.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>
                  Recently deleted ({deletedPhotos.length})
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                  {deletedPhotos.map((photo) => (
                    <div
                      key={photo.public_id}
                      className="space-y-2 rounded-md border border-dashed p-2 opacity-60"
                    >
                      <PhotoThumbnail photo={photo} />
                      <div className="text-xs text-muted-foreground">
                        deleted {photo.marked_deleted_at?.slice(0, 10)}
                      </div>
                      {canWrite && (
                        <Button
                          variant="outline"
                          size="sm"
                          disabled={actionInFlight}
                          onClick={() => handleRestore(photo.public_id)}
                        >
                          <Undo2 className="mr-1 h-3 w-3" />
                          Restore
                        </Button>
                      )}
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
