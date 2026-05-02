// SESSION_017 — "Public Preview" surface for the dealer.
//
// Opens a shadcn Dialog showing a live iframe of /embed/assistant
// alongside the copyable HTML snippet a dealer drops into their
// own marketing site. The button itself lives in the OS topbar so
// it's reachable from any dealer-OS page, not just Overview.
//
// No backend coupling: the iframe URL is built from
// `window.location.origin` so the preview tracks whatever host
// the OS is running on (localhost in dev, the production hostname
// at deploy time).

import { useMemo, useState } from "react";
import { Check, Copy, ExternalLink, Eye } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

const EMBED_PATH = "/embed/assistant";

export default function PublicPreviewDialog() {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  // window.location is only read in the browser; safe here because
  // Vite renders client-side. Memoize so the snippet doesn't
  // change identity on every render.
  const origin = useMemo(() => {
    if (typeof window === "undefined") return "http://localhost:5173";
    return window.location.origin;
  }, []);

  const embedUrl = `${origin}${EMBED_PATH}`;
  const snippet = `<iframe
  src="${embedUrl}"
  width="100%"
  height="700"
  style="border: none; border-radius: 8px;"
></iframe>`;

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(snippet);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // Clipboard can fail in restricted contexts; do nothing —
      // the snippet is still selectable in the textarea.
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <Button
        type="button"
        variant="outline"
        size="sm"
        className="gap-1.5"
        onClick={() => setOpen(true)}
      >
        <Eye className="h-3.5 w-3.5" />
        Public Preview
      </Button>

      <DialogContent
        className="sm:max-w-3xl"
        // The dialog renders a live iframe of the dealer's own embed
        // surface — auto-focusing into it on open would steal focus
        // away from the description. Keep focus on the dialog.
        onOpenAutoFocus={(e) => e.preventDefault()}
      >
        <DialogHeader>
          <DialogTitle>Public Preview</DialogTitle>
          <DialogDescription>
            This is how the assistant appears on your website.
          </DialogDescription>
        </DialogHeader>

        <div className="overflow-hidden rounded-lg border border-border bg-muted/40">
          <iframe
            title="Live Assistant embed preview"
            src={embedUrl}
            className="h-[480px] w-full"
            style={{ border: "none" }}
          />
        </div>

        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <label
              htmlFor="public-preview-snippet"
              className="text-xs font-medium uppercase tracking-wide text-muted-foreground"
            >
              Embed code
            </label>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="gap-1.5"
              onClick={handleCopy}
            >
              {copied ? (
                <>
                  <Check className="h-3.5 w-3.5 text-emerald-600" />
                  Copied
                </>
              ) : (
                <>
                  <Copy className="h-3.5 w-3.5" />
                  Copy
                </>
              )}
            </Button>
          </div>
          <textarea
            id="public-preview-snippet"
            readOnly
            value={snippet}
            spellCheck={false}
            onFocus={(e) => e.currentTarget.select()}
            className="w-full resize-none rounded-md border border-border bg-background p-3 font-mono text-xs text-foreground shadow-sm outline-none focus:border-primary/50"
            rows={6}
          />
          <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <ExternalLink className="h-3 w-3" />
            <a
              href={embedUrl}
              target="_blank"
              rel="noreferrer"
              className="underline-offset-2 hover:underline"
            >
              Open the embed in a new tab
            </a>
          </p>
        </div>
      </DialogContent>
    </Dialog>
  );
}
