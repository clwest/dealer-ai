// Milestone 3 · Increment 7 — three-step photo upload orchestrator.
//
// The M3.5 backend workflow is deliberately three steps:
//
//   1. requestPhotoUpload(content_type)  → PhotoUploadTarget
//   2. uploadPhotoBytes(target, file)    → 200/201 from storage
//   3. attachPhoto(storage_key, ...)     → ConditionFindingPhoto row
//
// The M3.7 spec explicitly requires the UI to preserve this
// three-step visibility rather than merging into a single helper.
// This component orchestrates them sequentially but keeps error
// handling per-step so the operator sees exactly which step failed.
//
// LOCAL vs S3 branching lives inside ``uploadPhotoBytes`` (api.ts)
// via the ``LOCAL_UPLOAD_URL_MARKER`` prefix check. The UI does not
// branch on adapter here.

import { useRef, useState } from "react";
import { ImagePlus, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/authFetch";
import {
  CONDITION_PHOTO_CONTENT_TYPES,
  attachPhoto,
  requestPhotoUpload,
  uploadPhotoBytes,
  type ConditionPhoto,
} from "@/lib/api";

type Step = "idle" | "requesting" | "uploading" | "attaching";

interface Props {
  stock: string;
  findingId: number;
  onAttached: (photo: ConditionPhoto) => void;
  disabled?: boolean;
}

function _humanizeError(err: unknown, step: Step): string {
  if (err instanceof ApiError) {
    if (err.status === 409) {
      if (step === "attaching") {
        return "Upload landed but the backend refused: metadata mismatch, already-attached, or completed report. Try again with a fresh photo.";
      }
      return "Server refused (409). The report may be locked or a duplicate exists.";
    }
    if (err.status === 400) {
      return "Bad request (400). Check that the file is an image (JPEG/PNG/HEIC/WebP).";
    }
    if (err.status === 502) {
      return "Storage provider unavailable. Try again in a moment.";
    }
    if (err.status === 404) {
      return "Finding not found or moved. Refresh the page.";
    }
    return `Server returned ${err.status}.`;
  }
  return "Upload failed. Check your connection and try again.";
}

export function PhotoUploadButton({
  stock,
  findingId,
  onAttached,
  disabled = false,
}: Props) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [step, setStep] = useState<Step>("idle");
  const [error, setError] = useState<string | null>(null);

  async function handleFile(file: File) {
    // Server enforces the whitelist too — this is a client-side
    // fast-fail so operators don't waste an upload request on a
    // .pdf.
    const detectedType = file.type || "";
    if (!CONDITION_PHOTO_CONTENT_TYPES.includes(detectedType)) {
      setError(
        `Only JPEG / PNG / HEIC / WebP images are allowed. Selected type: ${detectedType || "unknown"}.`,
      );
      return;
    }

    setError(null);

    // Step 1: request upload target.
    let target;
    try {
      setStep("requesting");
      const res = await requestPhotoUpload(stock, findingId, detectedType);
      target = res.upload_target;
    } catch (err) {
      setError(_humanizeError(err, "requesting"));
      setStep("idle");
      return;
    }

    // Step 2: upload bytes (local receiver or presigned PUT — the
    // api helper branches on LOCAL_UPLOAD_URL_MARKER prefix).
    try {
      setStep("uploading");
      const { status } = await uploadPhotoBytes({
        stock,
        findingId,
        uploadTarget: target,
        contentType: detectedType,
        file,
      });
      if (status !== 200 && status !== 201 && status !== 204) {
        throw new ApiError(status, `Upload transport returned ${status}.`);
      }
    } catch (err) {
      setError(_humanizeError(err, "uploading"));
      setStep("idle");
      return;
    }

    // Step 3: attach — backend HEAD-verifies content type + size
    // against the actual object metadata.
    try {
      setStep("attaching");
      const { photo } = await attachPhoto(stock, findingId, {
        storage_key: target.storage_key,
        content_type: detectedType,
        size_bytes: file.size,
      });
      onAttached(photo);
    } catch (err) {
      setError(_humanizeError(err, "attaching"));
    } finally {
      setStep("idle");
    }
  }

  const busy = step !== "idle";
  const stepLabel: Record<Step, string> = {
    idle: "Upload photo",
    requesting: "Requesting upload URL…",
    uploading: "Uploading…",
    attaching: "Attaching…",
  };

  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center gap-2">
        <input
          ref={inputRef}
          type="file"
          accept="image/jpeg,image/png,image/heic,image/webp"
          className="sr-only"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) {
              void handleFile(f);
            }
            // Reset so selecting the same file twice re-fires the
            // change event.
            e.target.value = "";
          }}
          disabled={disabled || busy}
        />
        <Button
          type="button"
          size="sm"
          variant="outline"
          disabled={disabled || busy}
          onClick={() => inputRef.current?.click()}
          className="h-8 gap-1.5"
        >
          {busy ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
          ) : (
            <ImagePlus className="h-3.5 w-3.5" aria-hidden="true" />
          )}
          <span>{stepLabel[step]}</span>
        </Button>
      </div>
      {error ? (
        <p role="alert" className="text-xs text-rose-700">
          {error}
        </p>
      ) : null}
    </div>
  );
}
