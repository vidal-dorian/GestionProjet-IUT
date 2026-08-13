import { type FormEvent, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ApiError } from "../api/projects";
import { login } from "../api/auth";
import { listMembers, type Member } from "../api/members";

export default function LoginPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const [members, setMembers] = useState<Member[] | null>(null);
  const [memberId, setMemberId] = useState("");
  const [pin, setPin] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!projectId) return;
    listMembers(projectId)
      .then((list) => {
        setMembers(list);
        if (list.length > 0) setMemberId(String(list[0].id));
      })
      .catch(() => setError("Impossible de charger les membres pour le moment."));
  }, [projectId]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    if (!memberId || !/^\d{4}$/.test(pin)) {
      setError("Sélectionnez votre nom et saisissez un PIN à 4 chiffres.");
      return;
    }

    setSubmitting(true);
    try {
      await login(projectId!, Number(memberId), pin);
      navigate(`/projects/${projectId}/me`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Impossible de se connecter pour le moment.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="page">
      <Link to={`/projects/${projectId}`} className="back-link">
        ← Retour au projet
      </Link>
      <h1>Se connecter</h1>

      {members && members.length === 0 && <p>Aucun membre sur ce projet pour l'instant.</p>}

      {members && members.length > 0 && (
        <form onSubmit={handleSubmit} className="form form-inline">
          <label htmlFor="member-select">Nom</label>
          <select id="member-select" value={memberId} onChange={(e) => setMemberId(e.target.value)}>
            {members.map((member) => (
              <option key={member.id} value={member.id}>
                {member.name}
              </option>
            ))}
          </select>

          <label htmlFor="login-pin">PIN (4 chiffres)</label>
          <input
            id="login-pin"
            type="password"
            inputMode="numeric"
            maxLength={4}
            value={pin}
            onChange={(e) => setPin(e.target.value.replace(/\D/g, "").slice(0, 4))}
            required
          />

          {error && <p className="error">{error}</p>}

          <button type="submit" disabled={submitting}>
            {submitting ? "Connexion..." : "Se connecter"}
          </button>
        </form>
      )}
    </div>
  );
}
