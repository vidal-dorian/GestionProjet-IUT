import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { me, type SessionMember } from "../api/auth";

export default function MyPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const [member, setMember] = useState<SessionMember | null>(null);
  const [loading, setLoading] = useState(true);

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
      <Link to={`/projects/${projectId}`} className="back-link">
        ← Retour au projet
      </Link>
      <h1>Bonjour, {member.name}</h1>
      <p className="meta">Vous êtes identifié·e sur ce projet.</p>
    </div>
  );
}
