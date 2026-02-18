import { useEffect, useState } from "react";
import { Routes, Route, Navigate, useLocation, useNavigate } from "react-router-dom";

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
import { AgentPage } from "./pages/Agent";
import { LoginPage } from "./pages/Login";
import { SetupAdminPage } from "./pages/SetupAdmin";

interface AuthStatus {
  setup_required: boolean;
  authenticated: boolean;
  username: string | null;
}

function App() {
  const location = useLocation();
  const navigate = useNavigate();
  const [authChecked, setAuthChecked] = useState(false);

  // Pages that don't need the sidebar/header layout
  const noLayoutRoutes = ["/", "/setup", "/login", "/setup-admin"];
  const showLayout = !noLayoutRoutes.includes(location.pathname);

  useEffect(() => {
    // Skip auth check for pages that handle their own auth
    if (["/login", "/setup-admin"].includes(location.pathname)) {
      setAuthChecked(true);
      return;
    }

    fetch("/api/auth/status")
      .then((r) => r.json())
      .then((data: AuthStatus) => {
        if (data.setup_required) {
          navigate("/setup-admin", { replace: true });
        } else if (!data.authenticated) {
          navigate("/login", { replace: true });
        }
        setAuthChecked(true);
      })
      .catch(() => {
        // If auth endpoint fails (e.g. no users table yet), proceed
        setAuthChecked(true);
      });
  }, [location.pathname, navigate]);

  if (!authChecked) {
    return null; // Brief flash-free loading
  }

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
            <Route path="/agent" element={<AgentPage />} />
            <Route path="*" element={<Navigate to="/repositories" replace />} />
          </Routes>
        </Layout>
      ) : (
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/setup" element={<RepositorySetupPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/setup-admin" element={<SetupAdminPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      )}
    </>
  );
}

export default App;
