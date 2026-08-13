import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { logout, me, type SessionMember } from "../api/auth";

export default function MyPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const [member, setMember] = useState<SessionMember | null>(null);
  const [loading, setLoading] = useState(true);
  const [loggingOut, setLoggingOut] = useState(false);

  useEffect(() => {
    me()
      .then((current) => {
        if (current.project_id !== Number(projectId)) {
          navigate(`/projects/${projectId}/login`, { replace: true });
          return;
        }
        setMember(current);
      })
      .catch(() => navigate(`/projects/${projectId}/login`, { replace: true }))
      .finally(() => setLoading(false));
  }, [projectId, navigate]);

  async function handleLogout() {
    setLoggingOut(true);
    try {
      await logout();
      navigate(`/projects/${projectId}/login`, { replace: true });
    } finally {
      setLoggingOut(false);
    }
  }

  if (loading) {
    return (
      <div className="page">
        <p>Chargement...</p>
      </div>
    );
  }

  if (!member) {
    return null;
  }

  return (
    <div className="page">
      <div className="page-header">
        <Link to={`/projects/${projectId}`} className="back-link">
          ← Retour au projet
        </Link>
        <button type="button" onClick={handleLogout} disabled={loggingOut} className="button-secondary">
          {loggingOut ? "Déconnexion..." : "Se déconnecter"}
        </button>
      </div>
      <h1>Bonjour, {member.name}</h1>
      <p className="meta">Vous êtes identifié·e sur ce projet.</p>
    </div>
  );
}
