import { type FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ApiError, createProject } from "../api/projects";
import AppShell from "../components/AppShell";
import PageHeader from "../components/PageHeader";

export default function CreateProjectPage() {
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    if (!name.trim()) {
      setError("Le nom du projet est obligatoire.");
      return;
    }

    setSubmitting(true);
    try {
      const project = await createProject({
        name: name.trim(),
        description: description.trim() || undefined,
      });
      navigate(`/projects/${project.id}`);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Impossible de créer le projet pour le moment.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AppShell title="Nouveau projet">
    <div className="page">
      <Link to="/projects" className="back-link">
        ← Tous les projets
      </Link>
      <PageHeader title="Créer un projet" />
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
          {submitting ? "Création..." : "Créer le projet"}
        </button>
      </form>
    </div>
    </AppShell>
  );
}
