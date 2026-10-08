import time
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
        {
            "email": "alice@example.com",
            "aud": ["test-aud"],
            "iss": "https://myteam.cloudflareaccess.com",
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
        },
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


def test_email_listed_in_admin_emails_is_promoted_to_admin(client, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "admin_emails", "boss@test.local, Chef@Test.local")
    client.headers["X-Dev-Email"] = "chef@test.local"

    body = client.get("/api/me").json()
    assert body["is_admin"] is True
    assert client.get("/api/admin/membership-requests").status_code == 200


def test_existing_account_is_promoted_once_added_to_admin_emails(client, monkeypatch):
    from app.config import settings

    client.headers["X-Dev-Email"] = "alice@test.local"
    assert client.get("/api/me").json()["is_admin"] is False

    monkeypatch.setattr(settings, "admin_emails", "alice@test.local")
    assert client.get("/api/me").json()["is_admin"] is True


def test_email_not_listed_in_admin_emails_stays_regular(client, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "admin_emails", "boss@test.local")
    client.headers["X-Dev-Email"] = "alice@test.local"

    assert client.get("/api/me").json()["is_admin"] is False
    assert client.get("/api/admin/membership-requests").status_code == 403


def test_cross_site_write_is_rejected(client):
    client.headers["X-Dev-Email"] = "alice@test.local"
    response = client.post("/api/projects", json={"name": "CSRF"}, headers={"Origin": "https://evil.example"})
    assert response.status_code == 403
    response = client.post("/api/projects", json={"name": "CSRF"}, headers={"Sec-Fetch-Site": "cross-site"})
    assert response.status_code == 403
    assert client.get("/api/projects").status_code == 200


def test_same_origin_write_is_accepted(client):
    from app.config import settings

    client.headers["X-Dev-Email"] = "alice@test.local"
    allowed = settings.cors_origins.split(",")[0].strip()
    response = client.post(
        "/api/projects",
        json={"name": "Même origine"},
        headers={"Origin": allowed, "Sec-Fetch-Site": "same-origin"},
    )
    assert response.status_code == 201


def test_integrity_errors_become_conflicts(client, monkeypatch):
    # Simule deux créations simultanées de la même catégorie : la vérification
    # applicative passe, la contrainte d'unicité de la base refuse la seconde.
    from app import crud

    client.headers["X-Dev-Email"] = "alice@test.local"
    project = client.post("/api/projects", json={"name": "Projet course"}).json()
    assert client.post(f"/api/projects/{project['id']}/categories", json={"name": "Dev"}).status_code == 201
    monkeypatch.setattr(crud, "list_categories", lambda db, project_id: [])
    response = client.post(f"/api/projects/{project['id']}/categories", json={"name": "Dev"})
    assert response.status_code == 409


def test_same_host_write_is_accepted_even_if_not_listed_in_cors(client):
    # En production, nginx sert frontend et API sur le même domaine : la
    # requête vient de l'hôte appelé lui-même, même si CORS_ORIGINS est mal réglé.
    client.headers["X-Dev-Email"] = "alice@test.local"
    response = client.post(
        "/api/projects",
        json={"name": "Même hôte"},
        headers={"Origin": "https://suivi.exemple.com", "Host": "suivi.exemple.com", "Sec-Fetch-Site": "same-origin"},
    )
    assert response.status_code == 201
