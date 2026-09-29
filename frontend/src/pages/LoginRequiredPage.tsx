import type { AuthError } from "../context/AuthContext";

interface LoginRequiredPageProps {
  error: AuthError;
}

/* Affichée à la place de l'application quand /api/me échoue. Le bouton fait
   une navigation complète (pas un lien React Router) : c'est elle qui repasse
   par Cloudflare Access, lequel redirige vers la connexion Google si aucune
   session n'est active. */
export default function LoginRequiredPage({ error }: LoginRequiredPageProps) {
  const unauthenticated = error === "unauthenticated";
  return (
    <div className="page">
      <h1>{unauthenticated ? "Vous n'êtes pas connecté" : "Service indisponible"}</h1>
      <p className="description">
        {unauthenticated
          ? "Votre session a expiré ou vous vous êtes déconnecté. Connectez-vous avec votre compte Google pour continuer."
          : "L'application ne répond pas pour le moment. Réessayez dans quelques instants."}
      </p>
      <p>
        <a href="/" className="button-link">
          {unauthenticated ? "Se connecter" : "Réessayer"}
        </a>
      </p>
    </div>
  );
}
