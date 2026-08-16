import { Route, Routes } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import AdminMembershipRequestsPage from "./pages/AdminMembershipRequestsPage";
import CreateProjectPage from "./pages/CreateProjectPage";
import DashboardPage from "./pages/DashboardPage";
import HomePage from "./pages/HomePage";
import ProjectHomePage from "./pages/ProjectHomePage";
import ProjectListPage from "./pages/ProjectListPage";
import ProjectSettingsPage from "./pages/ProjectSettingsPage";
import SprintsPage from "./pages/SprintsPage";

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/projects" element={<ProjectListPage />} />
        <Route path="/projects/new" element={<CreateProjectPage />} />
        <Route path="/projects/:projectId" element={<ProjectHomePage />} />
        <Route path="/projects/:projectId/settings" element={<ProjectSettingsPage />} />
        <Route path="/projects/:projectId/dashboard" element={<DashboardPage />} />
        <Route path="/projects/:projectId/sprints" element={<SprintsPage />} />
        <Route path="/admin/demandes" element={<AdminMembershipRequestsPage />} />
      </Routes>
    </AuthProvider>
  );
}
