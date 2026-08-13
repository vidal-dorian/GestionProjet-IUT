import { Navigate, Route, Routes } from "react-router-dom";
import CreateProjectPage from "./pages/CreateProjectPage";
import ProjectPage from "./pages/ProjectPage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/projects/new" replace />} />
      <Route path="/projects/new" element={<CreateProjectPage />} />
      <Route path="/projects/:projectId" element={<ProjectPage />} />
    </Routes>
  );
}
