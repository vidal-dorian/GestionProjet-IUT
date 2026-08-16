/* Jeu d'icônes minimal, monochrome (currentColor) et cohérent avec le reste de
   l'interface : trait de 1.6, coins arrondis, grille 24. Volontairement inline —
   pas de dépendance externe pour une poignée de glyphes. */

interface IconProps {
  className?: string;
}

function svgProps(className?: string) {
  return {
    className: className ? `icon ${className}` : "icon",
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.6,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    "aria-hidden": true,
    focusable: false,
  };
}

export function IconClock({ className }: IconProps) {
  return (
    <svg {...svgProps(className)}>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 7.5V12l3 1.8" />
    </svg>
  );
}

export function IconChart({ className }: IconProps) {
  return (
    <svg {...svgProps(className)}>
      <path d="M4 19.5V10M10 19.5V5M16 19.5v-6.5M21 19.5H3" />
    </svg>
  );
}

/* Barres décalées façon Gantt : évoque le planning d'itérations, et reste
   distinct de l'icône Paramètres (curseurs) dans la barre latérale. */
export function IconSprint({ className }: IconProps) {
  return (
    <svg {...svgProps(className)}>
      <rect x="3.5" y="5" width="9" height="4" rx="1.5" />
      <rect x="8" y="14.5" width="12.5" height="4" rx="1.5" />
      <rect x="6" y="9.75" width="11" height="4" rx="1.5" />
    </svg>
  );
}

export function IconSettings({ className }: IconProps) {
  return (
    <svg {...svgProps(className)}>
      <path d="M4 7h9M17 7h3M4 17h3M11 17h9" />
      <circle cx="15" cy="7" r="2.2" />
      <circle cx="9" cy="17" r="2.2" />
    </svg>
  );
}

export function IconGrid({ className }: IconProps) {
  return (
    <svg {...svgProps(className)}>
      <rect x="3.5" y="3.5" width="7" height="7" rx="1.5" />
      <rect x="13.5" y="3.5" width="7" height="7" rx="1.5" />
      <rect x="3.5" y="13.5" width="7" height="7" rx="1.5" />
      <rect x="13.5" y="13.5" width="7" height="7" rx="1.5" />
    </svg>
  );
}

export function IconInbox({ className }: IconProps) {
  return (
    <svg {...svgProps(className)}>
      <path d="M3.5 13.5h4l1.2 2h6.6l1.2-2h4" />
      <path d="M5.6 5.5h12.8l2.1 8v4a2 2 0 0 1-2 2H5.5a2 2 0 0 1-2-2v-4z" />
    </svg>
  );
}

export function IconPlus({ className }: IconProps) {
  return (
    <svg {...svgProps(className)}>
      <path d="M12 5v14M5 12h14" />
    </svg>
  );
}

export function IconMenu({ className }: IconProps) {
  return (
    <svg {...svgProps(className)}>
      <path d="M4 7h16M4 12h16M4 17h16" />
    </svg>
  );
}

export function IconClose({ className }: IconProps) {
  return (
    <svg {...svgProps(className)}>
      <path d="M6 6l12 12M18 6L6 18" />
    </svg>
  );
}

export function IconChevron({ className }: IconProps) {
  return (
    <svg {...svgProps(className)}>
      <path d="M8 10l4 4 4-4" />
    </svg>
  );
}

export function IconLogout({ className }: IconProps) {
  return (
    <svg {...svgProps(className)}>
      <path d="M10 5.5H6.5a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2H10" />
      <path d="M14.5 15.5L18.5 12l-4-3.5M18 12H9" />
    </svg>
  );
}
