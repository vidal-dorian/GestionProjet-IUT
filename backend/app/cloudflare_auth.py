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
        # Clés gardées en cache une heure (rotation Cloudflare bien plus lente)
        # et délai court : un JWKS injoignable ne doit pas bloquer les workers
        # 30 s par requête.
        _jwks_client = PyJWKClient(certs_url, cache_keys=True, lifespan=3600, timeout=5)
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
            # Tolère un léger décalage d'horloge (le Raspberry Pi n'a pas
            # d'horloge matérielle) sans accepter de jeton nettement expiré.
            leeway=30,
            options={"require": ["exp", "iat", "aud", "iss"]},
        )
    except jwt.PyJWTError as exc:
        raise CloudflareAuthError(str(exc)) from exc

    email = payload.get("email")
    if not isinstance(email, str) or not email.strip():
        raise CloudflareAuthError("Le jeton Cloudflare Access ne contient pas d'adresse e-mail.")
    return email.strip().lower()
