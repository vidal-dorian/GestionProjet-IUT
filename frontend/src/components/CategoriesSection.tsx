import { type FormEvent, useEffect, useState } from "react";
import { createCategory, listCategories, type Category } from "../api/categories";
import { ApiError } from "../api/projects";

interface Props {
  projectId: number;
}

export default function CategoriesSection({ projectId }: Props) {
  const [categories, setCategories] = useState<Category[] | null>(null);
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function loadCategories() {
    return listCategories(projectId).then(setCategories);
  }

  useEffect(() => {
    loadCategories().catch(() => setError("Impossible de charger les catégories pour le moment."));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    if (!name.trim()) {
      setError("Le nom de la catégorie est obligatoire.");
      return;
    }

    setSubmitting(true);
    try {
      await createCategory(projectId, name.trim());
      setName("");
      await loadCategories();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Impossible de créer cette catégorie pour le moment.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="chart-section">
      <h2>Catégories</h2>

      <form onSubmit={handleSubmit} className="form form-inline">
        <label htmlFor="category-name">Nom de la catégorie</label>
        <input
          id="category-name"
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          maxLength={80}
          placeholder="Dev, documentation, réunion..."
        />

        {error && <p className="error">{error}</p>}

        <button type="submit" disabled={submitting}>
          {submitting ? "Création..." : "Ajouter la catégorie"}
        </button>
      </form>

      {categories && categories.length === 0 && <p>Aucune catégorie pour l'instant.</p>}

      {categories && categories.length > 0 && (
        <ul className="member-list">
          {categories.map((category) => (
            <li key={category.id}>
              <span>{category.name}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
