// SESSION_022 — assistant-first hero band for the public homepage.
//
// Pattern adapted from Hudiburg's hero (full-bleed background +
// search/CTA stack) but inverted: the AI Assistant is the primary
// conversion path, not a hidden chat bubble. The search bar in the
// reference becomes a "Talk to AI" CTA that scrolls to the
// embedded chat band below; the lifestyle chips become example
// prompts that prefill the assistant.
//
// SESSION_226 (TASK_walkable-demo-and-servers-up 1d): the hero
// visual pulls a featured vehicle from the AllowAny
// `/api/dealer-ai/showroom/vehicles/` endpoint via
// `listShowroomVehicles`. When the store has no photo on the
// featured vehicle, the background falls through to a solid brand-
// ink panel rather than a stock image the store doesn't own.

import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Bot, Car, ShieldCheck, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  listShowroomVehicles,
  type ShowroomVehicle,
} from "@/lib/showroomApi";
import { useBrand } from "@/lib/brand";

const TRUST_POINTS = [
  { label: "Current inventory", icon: Car },
  { label: "Payment-aware", icon: ShieldCheck },
  { label: "No pressure", icon: Sparkles },
];

const FALLBACK_INTENT_CHIPS = [
  "Family SUV",
  "Good on gas under $12k",
  "Trade-in value",
];

export default function Hero() {
  const brand = useBrand();
  const [heroVehicle, setHeroVehicle] = useState<ShowroomVehicle | null>(null);
  const [chips, setChips] = useState<string[]>(FALLBACK_INTENT_CHIPS);

  useEffect(() => {
    let cancelled = false;
    // Pull a broad enough sample to derive both the featured vehicle
    // and store-shaped chips. offset=5 keeps the featured slot from
    // colliding with the DealershipHomePage InventoryTeaser row.
    Promise.all([
      listShowroomVehicles({ limit: 1, offset: 5 }),
      listShowroomVehicles({ limit: 50, offset: 0 }),
    ])
      .then(([featuredResp, sampleResp]) => {
        if (cancelled) return;
        setHeroVehicle(featuredResp.results[0] ?? null);
        setChips(deriveIntentChips(sampleResp.results));
      })
      .catch(() => {
        /* silent — hero degrades to no-vehicle mode + fallback chips. */
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <section className="relative isolate min-h-[680px] overflow-hidden bg-brand-ink text-white">
      {heroVehicle?.image_url ? (
        <div
          className="absolute inset-0 -z-20"
          aria-hidden
        >
          <img
            src={heroVehicle.image_url}
            alt=""
            className="h-full w-full object-cover"
          />
        </div>
      ) : null}
      <div className="absolute inset-0 -z-10 bg-brand-ink/75" aria-hidden />
      <div className="absolute inset-x-0 bottom-0 -z-10 h-32 bg-gradient-to-t from-background to-transparent" />

      <div className="mx-auto grid w-full max-w-7xl items-center gap-12 px-4 py-14 sm:px-6 lg:grid-cols-[1.05fr_0.95fr] lg:gap-20 lg:px-8 lg:py-24">
        <div>
          <div className="inline-flex items-center gap-2 rounded-md border border-white/20 bg-white/10 px-3 py-1 text-xs font-medium uppercase tracking-[0.16em] text-white/80 backdrop-blur">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-70" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-400" />
            </span>
            AI Assistant · Live now
          </div>

          <h1 className="mt-5 text-balance text-4xl font-semibold leading-[1.05] sm:text-5xl lg:text-6xl">
            Find your next ride with{" "}
            help, not pressure.
          </h1>
          <p className="mt-5 max-w-xl text-base text-white/80 sm:text-lg">
            Tell {brand.dealershipName.replace(/'s$/i, "")}'s AI assistant what
            you need — budget, body style, payment, trade-in. It pulls from
            current inventory and connects you with a real human when you're
            ready.
          </p>

          <div className="mt-8 flex flex-wrap items-center gap-3">
            <Button
              asChild
              size="lg"
              className="h-12 gap-2 bg-white px-5 text-sm font-semibold text-brand-blue shadow-soft hover:bg-brand-mist"
            >
              <Link to="/assistant">
                <Bot className="h-5 w-5" />
                Talk to AI Assistant
              </Link>
            </Button>
            <Button
              asChild
              size="lg"
              variant="outline"
              className="h-12 gap-2 border-white/30 bg-transparent px-5 text-sm font-semibold text-white hover:bg-white/10 hover:text-white"
            >
              <Link to="/showroom">
                <Car className="h-5 w-5" />
                Browse Showroom
                <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
          </div>

          <div className="mt-6 flex flex-wrap gap-2">
            {chips.map((chip) => (
              <Link
                key={chip}
                to={`/assistant?prompt=${encodeURIComponent(chip)}`}
                className="rounded-full border border-white/20 bg-white/5 px-3 py-1.5 text-xs font-medium text-white/85 backdrop-blur hover:border-white/40 hover:bg-white/10 hover:text-white"
              >
                {chip}
              </Link>
            ))}
          </div>

          <div className="mt-10 grid grid-cols-3 gap-4 border-t border-white/10 pt-6 text-xs sm:max-w-md sm:text-sm">
            {TRUST_POINTS.map(({ label, icon: Icon }) => (
              <div key={label} className="flex items-center gap-2 text-white/85">
                <Icon className="h-4 w-4 text-brand-accent" />
                <span>{label}</span>
              </div>
            ))}
          </div>
        </div>

        <HeroVisual
          dealershipName={brand.dealershipName}
          featured={heroVehicle}
        />
      </div>
    </section>
  );
}

function roundUpTo(value: number, step: number): number {
  if (!Number.isFinite(value) || value <= 0) return 0;
  return Math.ceil(value / step) * step;
}

function formatUnderPrice(maxPrice: number): string {
  const rounded = roundUpTo(maxPrice, 1000);
  return `$${(rounded / 1000).toFixed(0)}k`;
}

function deriveIntentChips(sample: ShowroomVehicle[]): string[] {
  if (sample.length === 0) return FALLBACK_INTENT_CHIPS;
  const priceOf = (v: ShowroomVehicle) => Number.parseFloat(v.price) || 0;
  const trucks = sample.filter((v) => v.body_style === "truck");
  const cars = sample.filter(
    (v) => v.body_style === "car" || v.body_style === "ev",
  );
  const suvs = sample.filter((v) => v.body_style === "suv");
  const chips: string[] = [];
  if (trucks.length > 0) {
    const cap = Math.max(...trucks.map(priceOf));
    chips.push(`Truck under ${formatUnderPrice(cap)}`);
  }
  if (suvs.length > 0) {
    chips.push("Family SUV");
  }
  if (cars.length > 0) {
    const cap = Math.max(...cars.map(priceOf));
    chips.push(`Good on gas under ${formatUnderPrice(cap)}`);
  }
  chips.push("Trade-in value");
  return chips.length > 0 ? chips : FALLBACK_INTENT_CHIPS;
}

function HeroVisual({
  dealershipName,
  featured,
}: {
  dealershipName: string;
  featured: ShowroomVehicle | null;
}) {
  // Simulated chat preview — purely decorative, conveys what the
  // real assistant does without spinning up a session on every page
  // load. Real chat is the next section below. Match card falls
  // through to a generic "on the lot" line when no featured vehicle
  // is available (empty store or endpoint down).
  return (
    <div className="relative mx-auto w-full max-w-md lg:max-w-none">
      <div className="overflow-hidden rounded-lg border border-white/15 bg-brand-ink/90 shadow-2xl shadow-black/40 backdrop-blur">
        <div className="flex items-center gap-2 border-b border-white/10 px-4 py-3">
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-brand-blue">
            <Bot className="h-4 w-4 text-white" />
          </div>
          <div className="flex-1 leading-tight">
            <div className="text-xs font-semibold text-white">
              {`${dealershipName} Assistant`}
            </div>
            <div className="text-[10.5px] text-white/60">
              Current inventory · Payment-aware
            </div>
          </div>
          <span className="text-[10px] font-medium text-emerald-400">●  online</span>
        </div>

        <div className="space-y-3 px-4 py-5">
          <ChatRow
            who="user"
            text="I want something reliable under my budget."
          />
          {featured ? (
            <>
              <ChatRow
                who="ai"
                text={`Take a look at this one on the lot today — ${featured.display_name} at ${formatFeaturedPrice(
                  featured.price,
                )}.`}
              />
              <div className="rounded-lg border border-white/10 bg-white/5 p-3">
                <div className="text-[10px] uppercase tracking-wider text-white/50">
                  From the lot
                </div>
                <div className="mt-0.5 text-sm font-semibold text-white">
                  {featured.display_name}
                </div>
                <div className="mt-1 flex items-center justify-between text-xs text-white/70">
                  <span>Stock #{featured.stock_number}</span>
                  <span className="rounded-full bg-emerald-500/20 px-2 py-0.5 text-[10px] font-medium text-emerald-300">
                    {formatFeaturedPrice(featured.price)}
                  </span>
                </div>
              </div>
            </>
          ) : (
            <ChatRow
              who="ai"
              text="Tell me a monthly payment or a body style and I'll pull matches from what's on the lot right now."
            />
          )}
          <ChatRow who="user" text="Can I bring my trade-in?" />
          <div className="flex justify-start">
            <div className="rounded-2xl rounded-bl-sm bg-white/10 px-3 py-2 text-xs text-white/80">
              <span className="inline-flex items-center gap-1">
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-white/70" />
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-white/50" />
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-white/30" />
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function formatFeaturedPrice(raw: string): string {
  const value = Number.parseFloat(raw);
  if (!Number.isFinite(value) || value <= 0) return "";
  return `$${Math.round(value).toLocaleString()}`;
}

function ChatRow({ who, text }: { who: "user" | "ai"; text: string }) {
  if (who === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-lg rounded-br-sm bg-brand-accent px-3 py-2 text-xs text-white">
          {text}
        </div>
      </div>
    );
  }
  return (
    <div className="flex justify-start">
      <div className="max-w-[90%] rounded-lg rounded-bl-sm bg-white/10 px-3 py-2 text-xs text-white/90 ring-1 ring-white/10">
        {text}
      </div>
    </div>
  );
}
