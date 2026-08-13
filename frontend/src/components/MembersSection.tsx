import { type FormEvent, useEffect, useState } from "react";
import { ApiError } from "../api/projects";
import { createMember, deleteMember, listMembers, type Member } from "../api/members";

interface Props {
  projectId: number;
}

function formatHours(hours: number): string {
  const rounded = Math.round(hours * 10) / 10;
  return `${rounded} h`;
}

export default function MembersSection({ projectId }: Props) {
  const [members, setMembers] = useState<Member[] | null>(null);
  const [name, setName] = useState("");
  const [pin, setPin] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function loadMembers() {
    return listMembers(projectId).then(setMembers);
  }

  useEffect(() => {
    loadMembers().catch(() => setError("Impossible de charger les membres pour le moment."));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    if (!name.trim()) {
      setError("Le nom du membre est obligatoire.");
      return;
    }
    if (!/^\d{4}$/.test(pin)) {
      setError("Le PIN doit être composé de 4 chiffres.");
      return;
    }

    setSubmitting(true);
    try {
      await createMember(projectId, { name: name.trim(), pin });
      setName("");
      setPin("");
      await loadMembers();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Impossible d'ajouter ce membre pour le moment.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleRemove(member: Member) {
    const hoursNotice =
      member.total_hours > 0
        ? ` Les ${formatHours(member.total_hours)} qu'il/elle a saisies seront aussi définitivement supprimées.`
        : "";
    const confirmed = window.confirm(
      `Retirer ${member.name} du projet ? Cette action est irréversible.${hoursNotice}`,
    );
    if (!confirmed) return;

    try {
      await deleteMember(projectId, member.id);
      await loadMembers();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Impossible de retirer ce membre pour le moment.");
    }
  }

  return (
    <section className="members-section">
      <h2>Membres</h2>

      {members && members.length === 0 && <p>Aucun membre pour l'instant.</p>}

      {members && members.length > 0 && (
        <ul className="member-list">
          {members.map((member) => (
            <li key={member.id}>
              <span className="member-name">{member.name}</span>
              <span className="member-actions">
                <span className="member-hours">{formatHours(member.total_hours)}</span>
                <button type="button" className="link-button" onClick={() => handleRemove(member)}>
                  Retirer
                </button>
              </span>
            </li>
          ))}
        </ul>
      )}

      <form onSubmit={handleSubmit} className="form form-inline">
        <label htmlFor="member-name">Nom</label>
        <input
          id="member-name"
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          maxLength={80}
          required
        />

        <label htmlFor="member-pin">PIN (4 chiffres)</label>
        <input
          id="member-pin"
          type="password"
          inputMode="numeric"
          maxLength={4}
          value={pin}
          onChange={(e) => setPin(e.target.value.replace(/\D/g, "").slice(0, 4))}
          required
        />

        {error && <p className="error">{error}</p>}

        <button type="submit" disabled={submitting}>
          {submitting ? "Ajout..." : "Ajouter le membre"}
        </button>
      </form>
    </section>
  );
}
