"""환경변수 기반 설정 로더.

프로젝트 루트의 .env 파일을 읽는다(.env.example 참고).
어떤 플랫폼의 자격증명이 채워져 있는지에 따라 커넥터가 실모드/미설정을 판단한다.
"""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_ENV_LOADED = False


def load_env() -> None:
    """루트의 .env 를 읽어 os.environ 에 주입한다 (이미 있는 값은 유지)."""
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())
    _ENV_LOADED = True


def get(key: str, default: str = "") -> str:
    load_env()
    return os.environ.get(key, default)


def has_all(*keys: str) -> bool:
    """주어진 환경변수가 전부 설정되어 있으면 True."""
    return all(get(k) for k in keys)
