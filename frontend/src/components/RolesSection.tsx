import { type FormEvent, useEffect, useState } from "react";
import { createRole, deleteRole, listRoles, renameRole, type TeamRole } from "../api/roles";
import { ApiError } from "../api/projects";
import RenamableListItem from "./RenamableListItem";

interface Props {
  projectId: number;
}

export default function RolesSection({ projectId }: Props) {
  const [roles, setRoles] = useState<TeamRole[] | null>(null);
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  function loadRoles() {
    return listRoles(projectId).then(setRoles);
  }

  useEffect(() => {
    loadRoles().catch(() => setError("Impossible de charger les rôles pour le moment."));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    if (!name.trim()) {
      setError("Le nom du rôle est obligatoire.");
      return;
    }

    setSubmitting(true);
    try {
      await createRole(projectId, name.trim());
      setName("");
      await loadRoles();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Impossible de créer ce rôle pour le moment.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(roleId: number) {
    setDeletingId(roleId);
    try {
      await deleteRole(projectId, roleId);
      setRoles((current) => current?.filter((role) => role.id !== roleId) ?? current);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Impossible de supprimer ce rôle pour le moment.");
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <section className="chart-section">
      <h2>Rôles d'équipe</h2>
      <p className="meta">
        Utilisés pour indiquer qui occupe quel rôle sur chaque sprint, et repris dans les comptes-rendus (daily,
        rétrospective). Renommer un rôle conserve ses attributions.
      </p>

      <form onSubmit={handleSubmit} className="form form-inline">
        <label htmlFor="role-name">Nom du rôle</label>
        <input
          id="role-name"
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          maxLength={80}
          placeholder="Testeur, Scrum master..."
        />

        {error && <p className="error">{error}</p>}

        <button type="submit" disabled={submitting}>
          {submitting ? "Création..." : "Ajouter le rôle"}
        </button>
      </form>

      {roles && roles.length === 0 && <p>Aucun rôle pour l'instant.</p>}

      {roles && roles.length > 0 && (
        <ul className="member-list">
          {roles.map((role) => (
            <RenamableListItem
              key={role.id}
              name={role.name}
              inputLabel={`Nouveau nom du rôle ${role.name}`}
              maxLength={80}
              onRename={async (newName) => {
                await renameRole(projectId, role.id, newName);
                await loadRoles();
              }}
              extraActions={
                <button
                  type="button"
                  className="button-danger"
                  disabled={deletingId === role.id}
                  onClick={() => handleDelete(role.id)}
                >
                  Supprimer
                </button>
              }
            />
          ))}
        </ul>
      )}
    </section>
  );
}
