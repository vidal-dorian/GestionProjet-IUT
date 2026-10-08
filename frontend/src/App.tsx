import type { ReactNode } from "react";
import { Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import AdminMembershipRequestsPage from "./pages/AdminMembershipRequestsPage";
import CreateProjectPage from "./pages/CreateProjectPage";
import DashboardPage from "./pages/DashboardPage";
import HomePage from "./pages/HomePage";
import LoginRequiredPage from "./pages/LoginRequiredPage";
import ProjectHomePage from "./pages/ProjectHomePage";
import ProjectListPage from "./pages/ProjectListPage";
import ProfilePage from "./pages/ProfilePage";
import ProjectSettingsPage from "./pages/ProjectSettingsPage";
import ReportEditorPage from "./pages/ReportEditorPage";
import ReportsPage from "./pages/ReportsPage";
import SprintsPage from "./pages/SprintsPage";

function AuthGate({ children }: { children: ReactNode }) {
  const { account, loading, error } = useAuth();
  if (loading) {
    return (
      <div className="page">
        <p>Chargement...</p>
      </div>
    );
  }
  if (!account) return <LoginRequiredPage error={error ?? "unauthenticated"} />;
  return children;
}

export default function App() {
  return (
    <AuthProvider>
      <AuthGate>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/projects" element={<ProjectListPage />} />
          <Route path="/projects/new" element={<CreateProjectPage />} />
          <Route path="/projects/:projectId" element={<ProjectHomePage />} />
          <Route path="/projects/:projectId/settings" element={<ProjectSettingsPage />} />
          <Route path="/projects/:projectId/dashboard" element={<DashboardPage />} />
          <Route path="/projects/:projectId/sprints" element={<SprintsPage />} />
          <Route path="/projects/:projectId/reports" element={<ReportsPage />} />
          <Route path="/projects/:projectId/reports/:reportId" element={<ReportEditorPage />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/admin/demandes" element={<AdminMembershipRequestsPage />} />
        </Routes>
      </AuthGate>
    </AuthProvider>
  );
}
