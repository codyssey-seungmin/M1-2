from firebase_admin import auth
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .firebase import firebase_app


bearer = HTTPBearer(auto_error=False)


def current_uid(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="인증 토큰이 필요합니다.")
    app = firebase_app()
    try:
        decoded = auth.verify_id_token(credentials.credentials, app=app)
        uid = decoded.get("uid")
        if not isinstance(uid, str) or not uid:
            raise ValueError("Missing uid")
        return uid
    except (ValueError, auth.InvalidIdTokenError, auth.ExpiredIdTokenError, auth.RevokedIdTokenError) as exc:
        raise HTTPException(status_code=401, detail="인증 토큰이 유효하지 않습니다.") from exc
