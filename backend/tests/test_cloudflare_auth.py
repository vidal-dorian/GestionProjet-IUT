from unittest.mock import MagicMock, patch

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from app import cloudflare_auth
from app.config import settings


@pytest.fixture(autouse=True)
def _configure_cloudflare_settings(monkeypatch):
    monkeypatch.setattr(settings, "cloudflare_team_domain", "myteam.cloudflareaccess.com")
    monkeypatch.setattr(settings, "cloudflare_access_aud", "test-aud")
    cloudflare_auth._jwks_client = None
    yield
    cloudflare_auth._jwks_client = None


def _make_token(private_key, **claims):
    return jwt.encode(claims, private_key, algorithm="RS256")


def _patch_signing_key(private_key):
    public_key = private_key.public_key()
    mock_signing_key = MagicMock()
    mock_signing_key.key = public_key
    return patch.object(
        cloudflare_auth, "_get_jwks_client", return_value=MagicMock(get_signing_key_from_jwt=lambda token: mock_signing_key)
    )


def test_verify_access_jwt_returns_email_for_valid_token():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    token = _make_token(
        private_key,
        email="alice@example.com",
        aud=["test-aud"],
        iss="https://myteam.cloudflareaccess.com",
    )

    with _patch_signing_key(private_key):
        email = cloudflare_auth.verify_access_jwt(token)

    assert email == "alice@example.com"


def test_verify_access_jwt_rejects_wrong_audience():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    token = _make_token(
        private_key,
        email="alice@example.com",
        aud=["some-other-app"],
        iss="https://myteam.cloudflareaccess.com",
    )

    with _patch_signing_key(private_key):
        with pytest.raises(cloudflare_auth.CloudflareAuthError):
            cloudflare_auth.verify_access_jwt(token)


def test_verify_access_jwt_rejects_wrong_issuer():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    token = _make_token(
        private_key,
        email="alice@example.com",
        aud=["test-aud"],
        iss="https://someone-elses-team.cloudflareaccess.com",
    )

    with _patch_signing_key(private_key):
        with pytest.raises(cloudflare_auth.CloudflareAuthError):
            cloudflare_auth.verify_access_jwt(token)


def test_verify_access_jwt_rejects_token_without_email():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    token = _make_token(private_key, aud=["test-aud"], iss="https://myteam.cloudflareaccess.com")

    with _patch_signing_key(private_key):
        with pytest.raises(cloudflare_auth.CloudflareAuthError):
            cloudflare_auth.verify_access_jwt(token)


def test_verify_access_jwt_rejects_signature_from_different_key():
    signing_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    token = _make_token(
        signing_key,
        email="alice@example.com",
        aud=["test-aud"],
        iss="https://myteam.cloudflareaccess.com",
    )

    with _patch_signing_key(other_key):
        with pytest.raises(cloudflare_auth.CloudflareAuthError):
            cloudflare_auth.verify_access_jwt(token)
