import jwt
from jwt import PyJWKClient

from app.config import settings

CF_ACCESS_JWT_HEADER = "Cf-Access-Jwt-Assertion"


class CloudflareAuthError(Exception):
    pass


_jwks_client: PyJWKClient | None = None


def _get_jwks_client() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        certs_url = f"https://{settings.cloudflare_team_domain}/cdn-cgi/access/certs"
        _jwks_client = PyJWKClient(certs_url)
    return _jwks_client


def verify_access_jwt(token: str) -> str:
    """Validates a Cf-Access-Jwt-Assertion token and returns the verified email claim.

    Raises CloudflareAuthError if the token is missing, malformed, expired, signed by an
    unknown key, or issued for a different Access application (wrong audience).
    """
    try:
        signing_key = _get_jwks_client().get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=settings.cloudflare_access_aud,
            issuer=f"https://{settings.cloudflare_team_domain}",
        )
    except jwt.PyJWTError as exc:
        raise CloudflareAuthError(str(exc)) from exc

    email = payload.get("email")
    if not email:
        raise CloudflareAuthError("Le jeton Cloudflare Access ne contient pas d'adresse e-mail.")
    return email
