import { type FormEvent, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ApiError, deleteProject, getProject, updateProject } from "../api/projects";

export default function EditProjectPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const [projectName, setProjectName] = useState("");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    if (!projectId) return;
    getProject(projectId)
      .then((project) => {
        setProjectName(project.name);
        setName(project.name);
        setDescription(project.description ?? "");
      })
      .catch(() => setError("Ce projet est introuvable."))
      .finally(() => setLoading(false));
  }, [projectId]);

  async function handleDelete() {
    const confirmed = window.confirm(
      `Supprimer le projet « ${projectName} » ? Cette action est irréversible : tous les membres et toutes les heures saisies seront définitivement supprimés.`,
    );
    if (!confirmed) return;

    setDeleting(true);
    try {
      await deleteProject(projectId!);
      navigate("/");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Impossible de supprimer ce projet pour le moment.");
      setDeleting(false);
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    if (!name.trim()) {
      setError("Le nom du projet est obligatoire.");
      return;
    }

    setSubmitting(true);
    try {
      await updateProject(projectId!, {
        name: name.trim(),
        description: description.trim() || undefined,
      });
      navigate(`/projects/${projectId}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Impossible de modifier le projet pour le moment.");
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <div className="page">
        <p>Chargement...</p>
      </div>
    );
  }

  return (
    <div className="page">
      <Link to={`/projects/${projectId}`} className="back-link">
        ← Retour au projet
      </Link>
      <h1>Modifier le projet</h1>
      <form onSubmit={handleSubmit} className="form">
        <label htmlFor="name">Nom du projet *</label>
        <input
          id="name"
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          maxLength={120}
          required
        />

        <label htmlFor="description">Description</label>
        <textarea
          id="description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={4}
        />

        {error && <p className="error">{error}</p>}

        <button type="submit" disabled={submitting}>
          {submitting ? "Enregistrement..." : "Enregistrer"}
        </button>
      </form>

      <section className="danger-zone">
        <h2>Zone dangereuse</h2>
        <p className="meta">
          Supprimer ce projet supprime aussi définitivement tous ses membres et toutes les heures saisies.
        </p>
        <button type="button" className="button-danger" onClick={handleDelete} disabled={deleting}>
          {deleting ? "Suppression..." : "Supprimer le projet"}
        </button>
      </section>
    </div>
  );
}
