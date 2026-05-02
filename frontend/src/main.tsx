import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";

import App from "@/App";
import AdvisorWorkspacePage from "@/pages/AdvisorWorkspacePage";
import DealerAIDemo from "@/pages/DealerAIDemo";
import DealerAdmin from "@/pages/DealerAdmin";
import DealershipHomePage from "@/pages/DealershipHomePage";
import DealerOnboardingPage from "@/pages/DealerOnboardingPage";
import DealerOverviewPage from "@/pages/DealerOverviewPage";
import EmbedAssistantPage from "@/pages/EmbedAssistantPage";
import InventoryPreviewPage from "@/pages/InventoryPreviewPage";
import LeadsPage from "@/pages/LeadsPage";
import LiveAssistantPage from "@/pages/LiveAssistantPage";
import ManagerChatPage from "@/pages/ManagerChatPage";
import PublicAssistantPage from "@/pages/PublicAssistantPage";
import PublicShowroomPage from "@/pages/PublicShowroomPage";
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
        {/* Public embed surface — rendered OUTSIDE the OS shell so a
            dealer can drop it into their public site via iframe
            without inheriting any sidebar / topbar / dashboard
            chrome. Must come before the catch-all "/" route. */}
        <Route path="/embed/assistant" element={<EmbedAssistantPage />} />

        <Route index element={<DealershipHomePage />} />
        <Route path="/assistant" element={<PublicAssistantPage />} />
        <Route path="/showroom" element={<PublicShowroomPage />} />

        <Route element={<App />}>
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
