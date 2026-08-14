import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { type Account, me } from "../api/auth";
import { listProjectMembers, removeProjectMember } from "../api/admin";
import { getProject, type Project } from "../api/projects";
import ContributorsSection from "../components/ContributorsSection";
import ProjectSwitcher from "../components/ProjectSwitcher";

export default function ProjectPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [project, setProject] = useState<Project | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isAdmin, setIsAdmin] = useState(false);
  const [members, setMembers] = useState<Account[] | null>(null);
  const [removingId, setRemovingId] = useState<number | null>(null);
  const [membersError, setMembersError] = useState<string | null>(null);

  useEffect(() => {
    if (!projectId) return;
    getProject(projectId)
      .then(setProject)
      .catch(() => setError("Ce projet est introuvable."));
  }, [projectId]);

  useEffect(() => {
    if (!projectId) return;
    me()
      .then((account) => {
        setIsAdmin(account.is_admin);
        if (!account.is_admin) return;
        return listProjectMembers(projectId)
          .then(setMembers)
          .catch(() => setMembersError("Impossible de charger les membres pour le moment."));
      })
      .catch(() => setIsAdmin(false));
  }, [projectId]);

  async function handleRemoveMember(accountId: number) {
    if (!projectId) return;
    setRemovingId(accountId);
    try {
      await removeProjectMember(projectId, accountId);
      setMembers((current) => current?.filter((m) => m.id !== accountId) ?? current);
    } catch {
      setMembersError("Impossible de retirer ce membre pour le moment.");
    } finally {
      setRemovingId(null);
    }
  }

  if (error) {
    return (
      <div className="page">
        <p className="error">{error}</p>
        <Link to="/">Retour à l'accueil</Link>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="page">
        <p>Chargement...</p>
      </div>
    );
  }

  return (
    <div className="page">
      <div className="page-header">
        <Link to="/" className="back-link">
          ← Retour aux projets
        </Link>
        <div className="page-header-actions">
          <ProjectSwitcher currentProjectId={project.id} />
          <Link to={`/projects/${project.id}/edit`} className="button-secondary">
            Modifier
          </Link>
          <Link to={`/projects/${project.id}/dashboard`} className="button-secondary">
            Dashboard
          </Link>
          <Link to={`/projects/${project.id}/me`} className="button-link">
            Mes heures
          </Link>
        </div>
      </div>
      <h1>{project.name}</h1>
      {project.description && <p className="description">{project.description}</p>}
      <p className="meta">
        Créé le {new Date(project.created_at).toLocaleDateString("fr-FR")}
      </p>

      <ContributorsSection projectId={project.id} />

      {isAdmin && (
        <section className="member-management">
          <h2>Membres du projet</h2>
          {membersError && <p className="error">{membersError}</p>}
          {members === null && <p>Chargement...</p>}
          {members && members.length === 0 && <p>Aucun membre approuvé pour l'instant.</p>}
          {members && members.length > 0 && (
            <ul className="member-list">
              {members.map((member) => (
                <li key={member.id}>
                  <div>
                    <strong>{member.email}</strong>
                    {member.is_admin && <span className="badge">Administrateur</span>}
                  </div>
                  <button
                    type="button"
                    className="button-danger"
                    disabled={removingId === member.id}
                    onClick={() => handleRemoveMember(member.id)}
                  >
                    Retirer
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}
    </div>
  );
}
