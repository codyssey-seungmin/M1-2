import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parents[2] / ".env")


def allowed_origins() -> list[str]:
    return [origin.strip() for origin in os.getenv("ALLOWED_ORIGINS", "").split(",") if origin.strip()]


def openai_model() -> str:
    return os.getenv("OPENAI_MODEL", "").strip()
