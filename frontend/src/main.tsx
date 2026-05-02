import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import App from "@/App";
import AdvisorWorkspacePage from "@/pages/AdvisorWorkspacePage";
import DealerAIDemo from "@/pages/DealerAIDemo";
import DealerAdmin from "@/pages/DealerAdmin";
import DealerOnboardingPage from "@/pages/DealerOnboardingPage";
import SalesTeamPage from "@/pages/SalesTeamPage";
import "@/index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<App />}>
          <Route index element={<Navigate to="/dealer-ai-demo" replace />} />
          <Route path="dealer-ai-demo" element={<DealerAIDemo />} />
          <Route
            path="dealer-ai-onboarding"
            element={<DealerOnboardingPage />}
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
