import { Routes, Route, Navigate, useLocation } from "react-router-dom";

import { Layout } from "./components/Layout";
import { LandingPage } from "./pages/Landing";
import { RepositorySetupPage } from "./pages/RepositorySetup";
import { RepositoriesPage } from "./pages/Repositories";
import { AboutPage } from "./pages/About";
import { DashboardPage } from "./pages/Dashboard";
import { RunsPage } from "./pages/Runs";
import { RunDetailsPage } from "./pages/RunDetails";
import { SettingsPage } from "./pages/Settings";
import { RisksPage } from "./pages/Risks";
import { TrendsPage } from "./pages/Trends";
import { CujCoveragePage } from "./pages/CujCoverage";
import { AppDocPage } from "./pages/AppDoc";
import { FeatureDetailPage } from "./pages/FeatureDetail";
import { IntegrationsPage } from "./pages/Integrations";
import { ArchitecturePage } from "./pages/Architecture";

function App() {
  const location = useLocation();

  // Pages that don't need the sidebar/header layout
  const noLayoutRoutes = ["/", "/setup"];
  const showLayout = !noLayoutRoutes.includes(location.pathname);

  return (
    <>
      {showLayout ? (
        <Layout>
          <Routes>
            <Route path="/repositories" element={<RepositoriesPage />} />
            <Route path="/about" element={<AboutPage />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/runs" element={<RunsPage />} />
            <Route path="/runs/:runId" element={<RunDetailsPage />} />
            <Route path="/risks" element={<RisksPage />} />
            <Route path="/cuj" element={<CujCoveragePage />} />
            <Route path="/trends" element={<TrendsPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/doc" element={<AppDocPage />} />
            <Route path="/doc/features/:featureId" element={<FeatureDetailPage />} />
            <Route path="/doc/integrations" element={<IntegrationsPage />} />
            <Route path="/doc/architecture" element={<ArchitecturePage />} />
            <Route path="*" element={<Navigate to="/repositories" replace />} />
          </Routes>
        </Layout>
      ) : (
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/setup" element={<RepositorySetupPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      )}
    </>
  );
}

export default App;
