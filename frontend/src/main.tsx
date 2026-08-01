import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";

import App from "@/App";
import RequireAuth from "@/components/RequireAuth";
import AdvisorWorkspacePage from "@/pages/AdvisorWorkspacePage";
import DealerAIDemo from "@/pages/DealerAIDemo";
import DealerAdmin from "@/pages/DealerAdmin";
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
                path="dealer-ai-advisor/:slug"
                element={<AdvisorWorkspacePage />}
              />
            </Route>
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>,
);
