import { Route, Routes } from "react-router-dom";
import AdminMembershipRequestsPage from "./pages/AdminMembershipRequestsPage";
import CreateProjectPage from "./pages/CreateProjectPage";
import DashboardPage from "./pages/DashboardPage";
import HomePage from "./pages/HomePage";
import ProjectHomePage from "./pages/ProjectHomePage";
import ProjectListPage from "./pages/ProjectListPage";
import ProjectSettingsPage from "./pages/ProjectSettingsPage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/projects" element={<ProjectListPage />} />
      <Route path="/projects/new" element={<CreateProjectPage />} />
      <Route path="/projects/:projectId" element={<ProjectHomePage />} />
      <Route path="/projects/:projectId/settings" element={<ProjectSettingsPage />} />
      <Route path="/projects/:projectId/dashboard" element={<DashboardPage />} />
      <Route path="/admin/demandes" element={<AdminMembershipRequestsPage />} />
    </Routes>
  );
}
