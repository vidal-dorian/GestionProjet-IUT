import type { ReactNode } from "react";

interface PageHeaderProps {
  title: string;
  subtitle?: ReactNode;
  actions?: ReactNode;
}

/* En-tête de contenu : le titre à gauche, les actions primaires de la page
   toujours à droite au même endroit d'une page à l'autre — sur mobile les
   actions repassent sous le titre plutôt que de le comprimer. */
export default function PageHeader({ title, subtitle, actions }: PageHeaderProps) {
  return (
    <header className="content-header">
      <div className="content-header-text">
        <h1>{title}</h1>
        {subtitle && <p className="content-header-subtitle">{subtitle}</p>}
      </div>
      {actions && <div className="content-header-actions">{actions}</div>}
    </header>
  );
}
