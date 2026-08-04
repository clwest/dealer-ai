import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";

import App from "@/App";
import RequireAuth from "@/components/RequireAuth";
import AccountingJournalEntriesPage from "@/pages/AccountingJournalEntriesPage";
import AccountingJournalEntryDetailPage from "@/pages/AccountingJournalEntryDetailPage";
import AccountingTrialBalancePage from "@/pages/AccountingTrialBalancePage";
import AdvisorWorkspacePage from "@/pages/AdvisorWorkspacePage";
import DealerAnalyticsPage from "@/pages/DealerAnalyticsPage";
import DealerAIDemo from "@/pages/DealerAIDemo";
import DealerAdmin from "@/pages/DealerAdmin";
import DealerAiBhphNoteDetail from "@/pages/DealerAiBhphNoteDetail";
import DealerAiBhphPortfolio from "@/pages/DealerAiBhphPortfolio";
import DealerAiSalesBeBacks from "@/pages/DealerAiSalesBeBacks";
import DealerAiSalesFollowUps from "@/pages/DealerAiSalesFollowUps";
import DealerAiSalesLeads from "@/pages/DealerAiSalesLeads";
import DealerAiSalesTestDrives from "@/pages/DealerAiSalesTestDrives";
import DealerFandICompliance from "@/pages/DealerFandICompliance";
import DealerFandIDeals from "@/pages/DealerFandIDeals";
import DealershipHomePage from "@/pages/DealershipHomePage";
import DealerOnboardingPage from "@/pages/DealerOnboardingPage";
import DealerOverviewPage from "@/pages/DealerOverviewPage";
import EmbedAssistantPage from "@/pages/EmbedAssistantPage";
import InventoryPreviewPage from "@/pages/InventoryPreviewPage";
import VehicleConditionReportPage from "@/pages/VehicleConditionReportPage";
import VehicleLedgerPage from "@/pages/VehicleLedgerPage";
import VehicleLifecyclePage from "@/pages/VehicleLifecyclePage";
import VehicleListingEditorPage from "@/pages/VehicleListingEditorPage";
import VehiclePhotoGalleryPage from "@/pages/VehiclePhotoGalleryPage";
import VehicleReconPage from "@/pages/VehicleReconPage";
import VehicleSalePage from "@/pages/VehicleSalePage";
import LeadsPage from "@/pages/LeadsPage";
import LiveAssistantPage from "@/pages/LiveAssistantPage";
import LoginPage from "@/pages/LoginPage";
import ManagerChatPage from "@/pages/ManagerChatPage";
import PublicAssistantPage from "@/pages/PublicAssistantPage";
import PublicShowroomPage from "@/pages/PublicShowroomPage";
import SalesTeamPage from "@/pages/SalesTeamPage";
import { AuthProvider } from "@/lib/AuthContext";
import "@/index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter
      future={{
        v7_startTransition: true,
        v7_relativeSplatPath: true,
      }}
    >
      <AuthProvider>
        <Routes>
          {/* Public embed surface — rendered OUTSIDE the OS shell so a
              dealer can drop it into their public site via iframe
              without inheriting any sidebar / topbar / dashboard
              chrome. Must come before the catch-all "/" route. */}
          <Route path="/embed/assistant" element={<EmbedAssistantPage />} />

          {/* Public pages — no auth wrapper. Milestone 1 · Increment 4E
              non-goal: do not accidentally place customer-facing
              surfaces behind authentication. */}
          <Route index element={<DealershipHomePage />} />
          <Route path="/assistant" element={<PublicAssistantPage />} />
          <Route path="/showroom" element={<PublicShowroomPage />} />
          <Route path="/login" element={<LoginPage />} />

          {/* Operator shell — RequireAuth redirects anonymous users to
              /login and preserves the intended path via ?next=. Every
              child inside the App outlet inherits the gate. */}
          <Route element={<RequireAuth />}>
            <Route element={<App />}>
              <Route
                path="dealer-ai-overview"
                element={<DealerOverviewPage />}
              />
              <Route
                path="dealer-ai-live-assistant"
                element={<LiveAssistantPage />}
              />
              <Route
                path="dealer-ai-inventory"
                element={<InventoryPreviewPage />}
              />
              <Route
                path="dealer-ai-inventory/:stock/ledger"
                element={<VehicleLedgerPage />}
              />
              <Route
                path="dealer-ai-inventory/:stock/condition-report"
                element={<VehicleConditionReportPage />}
              />
              <Route
                path="dealer-ai-inventory/:stock/recon"
                element={<VehicleReconPage />}
              />
              <Route
                path="dealer-ai-inventory/:stock/lifecycle"
                element={<VehicleLifecyclePage />}
              />
              <Route
                path="dealer-ai-inventory/:stock/photos"
                element={<VehiclePhotoGalleryPage />}
              />
              <Route
                path="dealer-ai-inventory/:stock/listing"
                element={<VehicleListingEditorPage />}
              />
              <Route
                path="dealer-ai-inventory/:stock/sale"
                element={<VehicleSalePage />}
              />
              <Route path="dealer-ai-leads" element={<LeadsPage />} />
              <Route path="dealer-ai-demo" element={<DealerAIDemo />} />
              <Route
                path="dealer-ai-onboarding"
                element={<DealerOnboardingPage />}
              />
              <Route
                path="dealer-ai-manager-chat"
                element={<ManagerChatPage />}
              />
              <Route path="dealer-ai-admin" element={<DealerAdmin />} />
              <Route path="dealer-ai-admin/team" element={<SalesTeamPage />} />
              <Route
                path="dealer-ai-analytics"
                element={<DealerAnalyticsPage />}
              />
              <Route
                path="dealer-ai-advisor/:slug"
                element={<AdvisorWorkspacePage />}
              />
              {/* Milestone 10 · Increment 7 — F&I operator UI (two-
                  tab MVP per §1.8.d Option A). */}
              <Route
                path="dealer-ai-f-and-i"
                element={<DealerFandIDeals />}
              />
              <Route
                path="dealer-ai-f-and-i/:contract_id/compliance"
                element={<DealerFandICompliance />}
              />
              {/* Milestone 11 · Increment 6 — sales operator UI
                  (four MVP pages per §5.f Option B / Option C: leads
                  channel filter, test-drive log, follow-up work-
                  queue, be-back list). The M11.3 DealWriteup UI
                  landed at M32.2 (SESSION_208) as a Writeups panel
                  inside LeadDetailModal per MILESTONE_32_PLANNING.md
                  §5.b D4-revised². */}
              <Route
                path="dealer-ai-sales/leads"
                element={<DealerAiSalesLeads />}
              />
              <Route
                path="dealer-ai-sales/test-drives"
                element={<DealerAiSalesTestDrives />}
              />
              <Route
                path="dealer-ai-sales/follow-ups"
                element={<DealerAiSalesFollowUps />}
              />
              <Route
                path="dealer-ai-sales/be-backs"
                element={<DealerAiSalesBeBacks />}
              />
              {/* Milestone 12 · Increment 7 (SESSION_127) — BHPH
                  portfolio operator UI MVP per §5.f Option C.
                  Portfolio dashboard + per-note detail ship;
                  collection-contact and repo-order UI defer to a
                  follow-on. */}
              <Route
                path="dealer-ai-bhph/portfolio"
                element={<DealerAiBhphPortfolio />}
              />
              <Route
                path="dealer-ai-bhph/notes/:pk"
                element={<DealerAiBhphNoteDetail />}
              />
              {/* Milestone 14 · Increment 2 (SESSION_135) — accounting
                  operator UI. First route of the new
                  ``dealer-ai-accounting/*`` group per §5.d Option A.
                  Consumes the M13.3 trial-balance endpoint. Journal-
                  entry browser + detail land at M14.3; reversal
                  dialog + cost-posting failure card at M14.4. */}
              <Route
                path="dealer-ai-accounting/trial-balance"
                element={<AccountingTrialBalancePage />}
              />
              {/* Milestone 14 · Increment 3 (SESSION_136) — journal-
                  entry browser + detail. Consumes the M14.1 list
                  endpoint + the M13.1 retrieve endpoint. Reversal
                  dialog wires at M14.4 per §5.e Option A. */}
              <Route
                path="dealer-ai-accounting/journal-entries"
                element={<AccountingJournalEntriesPage />}
              />
              <Route
                path="dealer-ai-accounting/journal-entries/:pk"
                element={<AccountingJournalEntryDetailPage />}
              />
            </Route>
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>,
);
