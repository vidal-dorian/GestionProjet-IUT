import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  approveMembershipRequest,
  listMembershipRequests,
  rejectMembershipRequest,
  type MembershipRequest,
} from "../api/admin";
import { me } from "../api/auth";
import { ApiError } from "../api/projects";

export default function AdminMembershipRequestsPage() {
  const [authorized, setAuthorized] = useState<boolean | null>(null);
  const [requests, setRequests] = useState<MembershipRequest[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [decidingId, setDecidingId] = useState<number | null>(null);

  useEffect(() => {
    me()
      .then((account) => {
        setAuthorized(account.is_admin);
        if (!account.is_admin) return;
        return listMembershipRequests()
          .then(setRequests)
          .catch(() => setError("Impossible de charger les demandes pour le moment."));
      })
      .catch(() => setAuthorized(false));
  }, []);

  async function handleDecision(requestId: number, decide: (id: number) => Promise<MembershipRequest>) {
    setDecidingId(requestId);
    try {
      await decide(requestId);
      setRequests((current) => current?.filter((r) => r.id !== requestId) ?? current);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Impossible de traiter cette demande pour le moment.");
    } finally {
      setDecidingId(null);
    }
  }

  if (authorized === null) {
    return (
      <div className="page">
        <p>Chargement...</p>
      </div>
    );
  }

  if (!authorized) {
    return (
      <div className="page">
        <p className="error">Réservé aux administrateurs.</p>
        <Link to="/">← Retour aux projets</Link>
      </div>
    );
  }

  return (
    <div className="page">
      <div className="page-header">
        <Link to="/" className="back-link">
          ← Retour aux projets
        </Link>
      </div>
      <h1>Demandes d'adhésion</h1>

      {error && <p className="error">{error}</p>}

      {requests && requests.length === 0 && <p>Aucune demande en attente.</p>}

      {requests && requests.length > 0 && (
        <ul className="member-list">
          {requests.map((request) => (
            <li key={request.id}>
              <div>
                <strong>{request.account_email}</strong>
                <p className="meta">
                  Souhaite rejoindre « {request.project_name} », demandé le{" "}
                  {new Date(request.created_at).toLocaleDateString("fr-FR")}
                </p>
              </div>
              <div className="member-actions">
                <button
                  type="button"
                  className="button-secondary"
                  disabled={decidingId === request.id}
                  onClick={() => handleDecision(request.id, approveMembershipRequest)}
                >
                  Approuver
                </button>
                <button
                  type="button"
                  className="button-danger"
                  disabled={decidingId === request.id}
                  onClick={() => handleDecision(request.id, rejectMembershipRequest)}
                >
                  Refuser
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
