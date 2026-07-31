// SESSION_022 — public dealership homepage.
//
// This is the Monday-demo surface: a real dealership homepage whose
// primary conversion path is the AI assistant, not a tiny widget or an
// operator dashboard. It uses the same AssistantChat implementation
// through AssistantBand, so the demo exercises the production chat
// surface without changing chat behavior.

import { Link } from "react-router-dom";
import { ArrowRight, BadgeCheck, Bot, Clock, ShieldCheck } from "lucide-react";

import AssistantBand from "@/components/dealership/AssistantBand";
import Hero from "@/components/dealership/Hero";
import SiteFooter from "@/components/dealership/SiteFooter";
import SiteNav from "@/components/dealership/SiteNav";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  SAMPLE_INVENTORY,
  type SampleInventoryVehicle,
} from "@/data/sampleInventory";
import { useBrand } from "@/lib/brand";
import { formatCurrency } from "@/lib/utils";

const FEATURED = SAMPLE_INVENTORY.slice(0, 3);

export default function DealershipHomePage() {
  const brand = useBrand();

  return (
    <div className="min-h-screen bg-background text-foreground">
      <SiteNav />
      <main>
        <Hero />
        <AssistantBand />
        <InventoryTeaser />
        <section id="trust" className="border-b border-border bg-muted/40 py-14">
          <div className="mx-auto grid w-full max-w-7xl gap-4 px-4 sm:px-6 lg:grid-cols-3 lg:px-8">
            <TrustItem
              icon={Bot}
              title="Start with a conversation"
              body="Describe the vehicle, budget, payment, or trade-in situation in plain language."
            />
            <TrustItem
              icon={ShieldCheck}
              title="See the math clearly"
              body="The assistant uses backend payment logic and keeps detailed numbers on the vehicle cards."
            />
            <TrustItem
              icon={BadgeCheck}
              title="Finish with a real person"
              body={`When the shopper is ready, a ${brand.storeLocation} advisor gets the context.`}
            />
          </div>
        </section>
        <section id="finance" className="border-b border-border bg-background py-14">
          <div className="mx-auto grid w-full max-w-7xl gap-8 px-4 sm:px-6 lg:grid-cols-[0.9fr_1.1fr] lg:px-8">
            <div>
              <Badge variant="outline" className="mb-3">
                Finance
              </Badge>
              <h2 className="text-3xl font-semibold tracking-tight">
                Shop by payment before you shop by stock number.
              </h2>
            </div>
            <div className="grid gap-3 sm:grid-cols-3">
              {[
                "$400/mo sedan",
                "$500/mo 4WD truck",
                "Cash commuter car",
              ].map((prompt) => (
                <Link
                  key={prompt}
                  to={`/assistant?prompt=${encodeURIComponent(prompt)}`}
                  className="rounded-lg border border-border bg-card p-4 text-sm font-medium shadow-soft transition hover:border-primary/40 hover:text-primary"
                >
                  {prompt}
                  <ArrowRight className="mt-4 h-4 w-4" />
                </Link>
              ))}
            </div>
          </div>
        </section>
        <section
          id="trade-in"
          className="border-b border-border bg-brand-ink py-14 text-white"
        >
          <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 sm:px-6 lg:flex-row lg:items-center lg:justify-between lg:px-8">
            <div className="max-w-2xl">
              <div className="mb-3 inline-flex items-center gap-2 rounded-md bg-white/10 px-2.5 py-1 text-xs font-medium uppercase tracking-[0.14em] text-white/70">
                <Clock className="h-3.5 w-3.5" />
                Quick handoff
              </div>
              <h2 className="text-3xl font-semibold tracking-tight">
                Bring the trade-in question into the same chat.
              </h2>
              <p className="mt-3 text-sm text-white/70">
                The assistant can capture the vehicle story, narrow the lot,
                and hand the whole conversation to the sales team.
              </p>
            </div>
            <Button
              asChild
              size="lg"
              className="h-11 gap-2 bg-white px-4 text-brand-ink hover:bg-brand-mist"
            >
              <Link to="/assistant?prompt=I have a trade-in and need a truck">
                Ask about my trade
                <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
          </div>
        </section>
        <section id="about" className="bg-background py-14">
          <div className="mx-auto grid w-full max-w-7xl gap-8 px-4 sm:px-6 lg:grid-cols-[0.75fr_1.25fr] lg:px-8">
            <div>
              <Badge variant="outline" className="mb-3">
                {brand.storeLocation}
              </Badge>
              <h2 className="text-3xl font-semibold tracking-tight">
                {brand.dealershipName} online, with the assistant up front.
              </h2>
            </div>
            <p className="text-base leading-7 text-muted-foreground">
              This demo keeps the dealership familiar: showroom, finance,
              trade-in, and visit information are still here. The difference is
              the first step. Shoppers can tell the assistant what they are
              trying to solve, then move into inventory with context already
              attached.
            </p>
          </div>
        </section>
      </main>
      <SiteFooter />
    </div>
  );
}

function InventoryTeaser() {
  return (
    <section id="showroom" className="border-b border-border bg-background py-14">
      <div className="mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <Badge variant="outline" className="mb-3">
              Showroom
            </Badge>
            <h2 className="text-3xl font-semibold tracking-tight">
              A few vehicles from the lot.
            </h2>
          </div>
          <Button asChild variant="outline" className="gap-2">
            <Link to="/showroom">
              Browse showroom
              <ArrowRight className="h-4 w-4" />
            </Link>
          </Button>
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          {FEATURED.map((vehicle) => (
            <FeaturedVehicle key={vehicle.vin} vehicle={vehicle} />
          ))}
        </div>
      </div>
    </section>
  );
}

function FeaturedVehicle({ vehicle }: { vehicle: SampleInventoryVehicle }) {
  return (
    <article className="overflow-hidden rounded-lg border border-border bg-card shadow-soft">
      <div className="aspect-[16/10] overflow-hidden bg-muted">
        <img
          src={vehicle.image_url}
          alt={vehicle.display_name}
          className="h-full w-full object-cover"
          loading="lazy"
        />
      </div>
      <div className="space-y-3 p-4">
        <div>
          <div className="text-sm font-semibold leading-tight">
            {vehicle.display_name}
          </div>
          <div className="mt-1 text-xs text-muted-foreground">
            Stock #{vehicle.stock_number} · {vehicle.drivetrain}
          </div>
        </div>
        <div className="flex items-center justify-between">
          <div className="text-lg font-bold text-primary">
            {formatCurrency(vehicle.price)}
          </div>
          <Button asChild size="sm" variant="ghost" className="gap-1.5">
            <Link
              to={`/assistant?prompt=${encodeURIComponent(
                `Tell me if the ${vehicle.display_name} fits my budget`,
              )}`}
            >
              <Bot className="h-3.5 w-3.5" />
              Ask AI
            </Link>
          </Button>
        </div>
      </div>
    </article>
  );
}

function TrustItem({
  icon: Icon,
  title,
  body,
}: {
  icon: typeof Bot;
  title: string;
  body: string;
}) {
  return (
    <div className="rounded-lg border border-border bg-card p-5 shadow-soft">
      <Icon className="h-5 w-5 text-primary" />
      <h3 className="mt-4 text-base font-semibold">{title}</h3>
      <p className="mt-2 text-sm leading-6 text-muted-foreground">{body}</p>
    </div>
  );
}
