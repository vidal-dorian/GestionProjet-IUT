import type { UserStoryRow } from "../api/reports";

interface Props {
  rows: UserStoryRow[];
  onChange: (rows: UserStoryRow[]) => void;
  onFillFromGithub: () => void;
  filling: boolean;
  fillLabel: string;
}

/* Tableau Référence / Nom des US : pré-rempli depuis GitHub, mais modifiable à
   la main (US hors GitHub, intitulé à reformuler pour le client...). */
export default function UserStoryTableEditor({ rows, onChange, onFillFromGithub, filling, fillLabel }: Props) {
  function update(index: number, patch: Partial<UserStoryRow>) {
    onChange(rows.map((row, i) => (i === index ? { ...row, ...patch } : row)));
  }

  return (
    <div className="us-table-editor">
      {rows.length === 0 ? (
        <p className="meta">Aucune user story dans le tableau.</p>
      ) : (
        <table className="us-table">
          <thead>
            <tr>
              <th scope="col">Référence</th>
              <th scope="col">Nom</th>
              <th scope="col">
                <span className="visually-hidden">Actions</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, index) => (
              <tr key={index}>
                <td>
                  <input
                    type="text"
                    aria-label={`Référence de la ligne ${index + 1}`}
                    value={row.reference}
                    maxLength={50}
                    onChange={(e) => update(index, { reference: e.target.value })}
                  />
                </td>
                <td>
                  <input
                    type="text"
                    aria-label={`Nom de la ligne ${index + 1}`}
                    value={row.name}
                    maxLength={500}
                    onChange={(e) => update(index, { name: e.target.value })}
                  />
                </td>
                <td>
                  <button
                    type="button"
                    className="link-button"
                    onClick={() => onChange(rows.filter((_, i) => i !== index))}
                  >
                    Retirer
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <div className="form-actions us-table-actions">
        <button type="button" className="button-secondary" onClick={() => onChange([...rows, { reference: "#", name: "" }])}>
          Ajouter une ligne
        </button>
        <button type="button" className="button-secondary" onClick={onFillFromGithub} disabled={filling}>
          {filling ? "Chargement..." : fillLabel}
        </button>
      </div>
    </div>
  );
}
