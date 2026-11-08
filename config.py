
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

DATABASE_DIR = BASE_DIR / "instance"
DATABASE_DIR.mkdir(parents=True, exist_ok=True)


class Config:

    SECRET_KEY = os.environ.get(
        "SECRET_KEY",
        "talentiq-local-development-only-secret"
    )

    SQLALCHEMY_DATABASE_URI = (
        f"sqlite:///{(DATABASE_DIR / 'talentiq.db').as_posix()}"
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
