import { type ReactNode, useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import SidebarProjectPicker from "./SidebarProjectPicker";
import { IconChart, IconClock, IconClose, IconGrid, IconInbox, IconLogout, IconMenu, IconSettings, IconSprint } from "./icons";

export const LAST_PROJECT_STORAGE_KEY = "lastProjectId";

interface AppShellProps {
  children: ReactNode;
  /** Titre affiché dans la barre mobile (la barre latérale la remplace sur grand écran). */
  title: string;
  project?: { id: number; name: string };
  canManage?: boolean;
}

interface NavItem {
  to: string;
  label: string;
  icon: ReactNode;
  /** Actif uniquement sur une correspondance exacte (sinon, préfixe). */
  exact?: boolean;
}

export default function AppShell({ children, title, project, canManage = false }: AppShellProps) {
  const { account, isAdmin } = useAuth();
  const { pathname } = useLocation();
  const [drawerOpen, setDrawerOpen] = useState(false);

  useEffect(() => {
    if (project) localStorage.setItem(LAST_PROJECT_STORAGE_KEY, String(project.id));
  }, [project]);

  // Le tiroir mobile ne doit jamais survivre à une navigation : sans ça, on
  // atterrit sur la nouvelle page avec le menu encore ouvert par-dessus.
  useEffect(() => {
    setDrawerOpen(false);
  }, [pathname]);

  useEffect(() => {
    if (!drawerOpen) return;
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setDrawerOpen(false);
    }
    document.addEventListener("keydown", onKeyDown);
    document.body.classList.add("has-drawer-open");
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.body.classList.remove("has-drawer-open");
    };
  }, [drawerOpen]);

  const projectItems: NavItem[] = project
    ? [
        { to: `/projects/${project.id}`, label: "Saisie", icon: <IconClock />, exact: true },
        { to: `/projects/${project.id}/dashboard`, label: "Dashboard", icon: <IconChart /> },
        { to: `/projects/${project.id}/sprints`, label: "Sprints", icon: <IconSprint /> },
        ...(canManage
          ? [{ to: `/projects/${project.id}/settings`, label: "Paramètres", icon: <IconSettings /> }]
          : []),
      ]
    : [];

  const globalItems: NavItem[] = [
    { to: "/projects", label: "Tous les projets", icon: <IconGrid />, exact: true },
    ...(isAdmin ? [{ to: "/admin/demandes", label: "Demandes d'accès", icon: <IconInbox /> }] : []),
  ];

  function renderItem(item: NavItem) {
    const isActive = item.exact ? pathname === item.to : pathname.startsWith(item.to);
    return (
      <Link key={item.to} to={item.to} className={isActive ? "sidebar-link is-active" : "sidebar-link"}>
        <span className="sidebar-link-icon">{item.icon}</span>
        <span>{item.label}</span>
      </Link>
    );
  }

  return (
    <div className="shell">
      <header className="shell-topbar">
        <button
          type="button"
          className="shell-menu-button"
          aria-label="Ouvrir le menu"
          aria-expanded={drawerOpen}
          onClick={() => setDrawerOpen(true)}
        >
          <IconMenu />
        </button>
        <span className="shell-topbar-title">{title}</span>
      </header>

      {drawerOpen && (
        <div className="shell-backdrop" onClick={() => setDrawerOpen(false)} aria-hidden="true" />
      )}

      <aside className={drawerOpen ? "shell-sidebar is-open" : "shell-sidebar"}>
        <div className="sidebar-head">
          <SidebarProjectPicker currentProjectId={project?.id} currentProjectName={project?.name} />
          <button
            type="button"
            className="sidebar-close-button"
            aria-label="Fermer le menu"
            onClick={() => setDrawerOpen(false)}
          >
            <IconClose />
          </button>
        </div>

        <nav className="sidebar-nav">
          {projectItems.length > 0 && (
            <div className="sidebar-group">
              <p className="sidebar-group-label">Projet</p>
              {projectItems.map(renderItem)}
            </div>
          )}

          <div className="sidebar-group">
            <p className="sidebar-group-label">Navigation</p>
            {globalItems.map(renderItem)}
          </div>
        </nav>

        <div className="sidebar-foot">
          {account && (
            <span className="sidebar-account">
              <span className="sidebar-account-email">{account.email}</span>
              {isAdmin && <span className="badge">Admin</span>}
            </span>
          )}
          <a href="/cdn-cgi/access/logout" className="sidebar-link sidebar-link-quiet">
            <span className="sidebar-link-icon">
              <IconLogout />
            </span>
            <span>Se déconnecter</span>
          </a>
        </div>
      </aside>

      <main className="shell-main">{children}</main>
    </div>
  );
}
