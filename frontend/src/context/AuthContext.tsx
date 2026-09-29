import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { me, type Account } from "../api/auth";
import { ApiError } from "../api/projects";

/**
 * "unauthenticated" : pas de session Cloudflare Access valide (déconnexion,
 * session expirée). Cloudflare répond alors par une redirection vers sa page
 * de connexion, que fetch ne peut pas suivre (CORS) : l'appel échoue en
 * erreur réseau ou en 401/403 selon le cas.
 * "unavailable" : l'API répond mais en erreur serveur.
 */
export type AuthError = "unauthenticated" | "unavailable";

interface AuthState {
  account: Account | null;
  isAdmin: boolean;
  loading: boolean;
  error: AuthError | null;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthState>({
  account: null,
  isAdmin: false,
  loading: true,
  error: null,
  refresh: async () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [account, setAccount] = useState<Account | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<AuthError | null>(null);

  async function refresh() {
    try {
      const result = await me();
      setAccount(result);
      setError(null);
    } catch (err) {
      setAccount(null);
      setError(err instanceof ApiError && err.status >= 500 ? "unavailable" : "unauthenticated");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <AuthContext.Provider value={{ account, isAdmin: account?.is_admin ?? false, loading, error, refresh }}>
      {children}
    </AuthContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthState {
  return useContext(AuthContext);
}
