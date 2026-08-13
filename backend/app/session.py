from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.config import settings

SESSION_COOKIE_NAME = "session_token"
SESSION_MAX_AGE_SECONDS = 30 * 24 * 60 * 60  # 30 jours : la session doit persister entre les visites (US-08).

_serializer = URLSafeTimedSerializer(settings.secret_key, salt="member-session")


def create_session_token(member_id: int, project_id: int) -> str:
    return _serializer.dumps({"member_id": member_id, "project_id": project_id})


def read_session_token(token: str) -> dict | None:
    try:
        return _serializer.loads(token, max_age=SESSION_MAX_AGE_SECONDS)
    except (BadSignature, SignatureExpired):
        return None
