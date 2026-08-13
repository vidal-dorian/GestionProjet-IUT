import { Route, Routes } from "react-router-dom";
import CreateProjectPage from "./pages/CreateProjectPage";
import DashboardPage from "./pages/DashboardPage";
import LoginPage from "./pages/LoginPage";
import MyPage from "./pages/MyPage";
import ProjectListPage from "./pages/ProjectListPage";
import ProjectPage from "./pages/ProjectPage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<ProjectListPage />} />
      <Route path="/projects/new" element={<CreateProjectPage />} />
      <Route path="/projects/:projectId" element={<ProjectPage />} />
      <Route path="/projects/:projectId/login" element={<LoginPage />} />
      <Route path="/projects/:projectId/me" element={<MyPage />} />
      <Route path="/projects/:projectId/dashboard" element={<DashboardPage />} />
    </Routes>
  );
}
