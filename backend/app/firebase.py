import json
import os

import firebase_admin
from firebase_admin import credentials, firestore
from fastapi import HTTPException


def firebase_app():
    try:
        return firebase_admin.get_app()
    except ValueError:
        pass

    raw_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON", "").strip()
    key_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", "").strip()
    if raw_json:
        try:
            credential = credentials.Certificate(json.loads(raw_json))
        except (ValueError, TypeError) as exc:
            raise HTTPException(status_code=503, detail="Firebase 인증 설정이 올바르지 않습니다.") from exc
    elif key_path:
        try:
            credential = credentials.Certificate(key_path)
        except (ValueError, OSError) as exc:
            raise HTTPException(status_code=503, detail="Firebase 인증 파일을 읽을 수 없습니다.") from exc
    else:
        raise HTTPException(status_code=503, detail="Firebase 인증 설정이 필요합니다.")
    return firebase_admin.initialize_app(credential)


def get_db():
    return firestore.client(app=firebase_app())
