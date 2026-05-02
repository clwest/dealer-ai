import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import App from "@/App";
import AdvisorWorkspacePage from "@/pages/AdvisorWorkspacePage";
import DealerAIDemo from "@/pages/DealerAIDemo";
import DealerAdmin from "@/pages/DealerAdmin";
import DealerOnboardingPage from "@/pages/DealerOnboardingPage";
import DealerOverviewPage from "@/pages/DealerOverviewPage";
import InventoryPreviewPage from "@/pages/InventoryPreviewPage";
import LeadsPage from "@/pages/LeadsPage";
import LiveAssistantPage from "@/pages/LiveAssistantPage";
import ManagerChatPage from "@/pages/ManagerChatPage";
import SalesTeamPage from "@/pages/SalesTeamPage";
import "@/index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter
      future={{
        v7_startTransition: true,
        v7_relativeSplatPath: true,
      }}
    >
      <Routes>
        <Route path="/" element={<App />}>
          <Route
            index
            element={<Navigate to="/dealer-ai-overview" replace />}
          />
          <Route path="dealer-ai-overview" element={<DealerOverviewPage />} />
          <Route
            path="dealer-ai-live-assistant"
            element={<LiveAssistantPage />}
          />
          <Route
            path="dealer-ai-inventory"
            element={<InventoryPreviewPage />}
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
      </Routes>
    </BrowserRouter>
  </React.StrictMode>,
);
