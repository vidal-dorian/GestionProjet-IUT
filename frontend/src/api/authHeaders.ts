// In production, Cloudflare Access injects the Cf-Access-Jwt-Assertion header
// automatically — the frontend never needs to touch it. This header only
// exists to test locally against a backend running with
// DEV_BYPASS_AUTH_ENABLED=true (never set in production), by declaring
// VITE_DEV_EMAIL in a local .env file.
export function devAuthHeaders(): Record<string, string> {
  const devEmail = import.meta.env.VITE_DEV_EMAIL as string | undefined;
  return devEmail ? { "X-Dev-Email": devEmail } : {};
}
