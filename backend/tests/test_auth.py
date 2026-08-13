def test_me_without_authentication_returns_401(client):
    response = client.get("/api/me")
    assert response.status_code == 401


def test_me_with_dev_bypass_header_auto_provisions_account(client):
    client.headers["X-Dev-Email"] = "alice@test.local"

    response = client.get("/api/me")
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "alice@test.local"
    assert body["is_admin"] is False


def test_me_returns_the_same_account_across_requests(client):
    client.headers["X-Dev-Email"] = "alice@test.local"

    first = client.get("/api/me").json()
    second = client.get("/api/me").json()
    assert first["id"] == second["id"]


def test_dev_bypass_disabled_returns_401_even_with_header(client, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "dev_bypass_auth_enabled", False)
    client.headers["X-Dev-Email"] = "alice@test.local"

    response = client.get("/api/me")
    assert response.status_code == 401


def test_dev_bypass_header_is_ignored_once_cloudflare_is_configured(client, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "cloudflare_team_domain", "myteam.cloudflareaccess.com")
    monkeypatch.setattr(settings, "cloudflare_access_aud", "test-aud")
    client.headers["X-Dev-Email"] = "alice@test.local"

    response = client.get("/api/me")
    assert response.status_code == 401


def test_cloudflare_jwt_is_validated_end_to_end(client, monkeypatch):
    import jwt
    from cryptography.hazmat.primitives.asymmetric import rsa
    from unittest.mock import MagicMock

    from app import cloudflare_auth
    from app.config import settings

    monkeypatch.setattr(settings, "cloudflare_team_domain", "myteam.cloudflareaccess.com")
    monkeypatch.setattr(settings, "cloudflare_access_aud", "test-aud")

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    token = jwt.encode(
        {"email": "alice@example.com", "aud": ["test-aud"], "iss": "https://myteam.cloudflareaccess.com"},
        private_key,
        algorithm="RS256",
    )
    mock_signing_key = MagicMock()
    mock_signing_key.key = private_key.public_key()
    monkeypatch.setattr(
        cloudflare_auth,
        "_get_jwks_client",
        lambda: MagicMock(get_signing_key_from_jwt=lambda t: mock_signing_key),
    )

    response = client.get("/api/me", headers={"Cf-Access-Jwt-Assertion": token})
    assert response.status_code == 200
    assert response.json()["email"] == "alice@example.com"

    # An invalid/tampered token must be rejected, not silently accepted.
    bad_response = client.get("/api/me", headers={"Cf-Access-Jwt-Assertion": token + "tampered"})
    assert bad_response.status_code == 401
