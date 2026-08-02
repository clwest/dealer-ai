// Milestone 8 · Increment 5 (SESSION_098) — operator analytics page.
//
// Wires the four M8 dashboard tabs to the M8.1-M8.4 aggregation
// endpoints. Server-side role-gate
// (IsReconManagerSalesManagerOrOwnerAtActiveDealership) is the
// authoritative check — the frontend just renders whatever the
// backend permits.
//
// Tabs:
//
//   1. Acquisition & Recon Cost  — Q1 + Q3 (recon per source +
//                                  per vehicle-type)
//   2. Vendor Performance         — Q2 + Q4
//   3. Lifecycle Aging            — Q5 + Q8 + Q9 (per-stage trend +
//                                  frontline scorecard)
//   4. SLA Breach Patterns        — Q10
//
// Every tab uses the plain useEffect + useState + authFetch pattern
// that every operator page in this repo uses (see
// VehicleLedgerPage.tsx). No React Query — matches the convention.

import { useEffect, useState } from "react";

import { AcquisitionReconTab } from "@/components/analytics/AcquisitionReconTab";
import { LifecycleAgingTab } from "@/components/analytics/LifecycleAgingTab";
import { RealizedGrossTab } from "@/components/analytics/RealizedGrossTab";
import { SlaBreachTab } from "@/components/analytics/SlaBreachTab";
import { VendorPerformanceTab } from "@/components/analytics/VendorPerformanceTab";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";

const TAB_ITEMS = [
  { value: "acquisition", label: "Acquisition & Recon Cost" },
  { value: "vendor", label: "Vendor Performance" },
  { value: "aging", label: "Lifecycle Aging" },
  { value: "sla", label: "SLA Breach Patterns" },
  { value: "realized-gross", label: "Realized Gross" },
] as const;

type TabValue = (typeof TAB_ITEMS)[number]["value"];

const DEFAULT_TAB: TabValue = "acquisition";

export default function DealerAnalyticsPage() {
  // Persist the active tab in the URL hash so an operator can
  // deep-link to a specific dashboard view (e.g. /dealer-ai-analytics#vendor).
  const [activeTab, setActiveTab] = useState<TabValue>(() => {
    const hash = window.location.hash.replace("#", "");
    return isTabValue(hash) ? hash : DEFAULT_TAB;
  });

  useEffect(() => {
    // Update the URL hash without a full navigation. Using
    // history.replaceState avoids polluting the browser's back-
    // button history with every tab switch.
    window.history.replaceState(null, "", `#${activeTab}`);
  }, [activeTab]);

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-tight">
          Operational Intelligence
        </h1>
        <p className="text-sm text-muted-foreground">
          Aggregations over acquisition, recon, lifecycle aging,
          SLA-breach (M8.1–M8.4), and realized-gross (M9.3 + M9.4).
        </p>
      </header>

      <Tabs
        value={activeTab}
        onValueChange={(next) => {
          if (isTabValue(next)) setActiveTab(next);
        }}
      >
        <TabsList className="flex flex-wrap gap-1">
          {TAB_ITEMS.map((item) => (
            <TabsTrigger key={item.value} value={item.value}>
              {item.label}
            </TabsTrigger>
          ))}
        </TabsList>

        <TabsContent value="acquisition">
          <AcquisitionReconTab />
        </TabsContent>
        <TabsContent value="vendor">
          <VendorPerformanceTab />
        </TabsContent>
        <TabsContent value="aging">
          <LifecycleAgingTab />
        </TabsContent>
        <TabsContent value="sla">
          <SlaBreachTab />
        </TabsContent>
        <TabsContent value="realized-gross">
          <RealizedGrossTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}

function isTabValue(v: string): v is TabValue {
  return TAB_ITEMS.some((item) => item.value === v);
}
