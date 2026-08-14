import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { me, type Account } from "../api/auth";
import ProjectSwitcher from "../components/ProjectSwitcher";
import TimeEntriesSection from "../components/TimeEntriesSection";

export default function MyPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [account, setAccount] = useState<Account | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    me()
      .then(setAccount)
      .catch(() => setError("Authentification requise. Vérifiez que vous accédez à l'application via le lien fourni par votre administrateur."))
      .finally(() => setLoading(false));
  }, [projectId]);

  if (loading) {
    return (
      <div className="page">
        <p>Chargement...</p>
      </div>
    );
  }

  if (error || !account) {
    return (
      <div className="page">
        <p className="error">{error}</p>
        <Link to={`/projects/${projectId}`}>← Retour au projet</Link>
      </div>
    );
  }

  return (
    <div className="page">
      <div className="page-header">
        <Link to={`/projects/${projectId}`} className="back-link">
          ← Retour au projet
        </Link>
        <div className="page-header-actions">
          <ProjectSwitcher currentProjectId={projectId ? Number(projectId) : undefined} />
          <a href="/cdn-cgi/access/logout" className="button-secondary">
            Se déconnecter
          </a>
        </div>
      </div>
      <h1>Bonjour, {account.email}</h1>

      <TimeEntriesSection projectId={Number(projectId)} />
    </div>
  );
}
