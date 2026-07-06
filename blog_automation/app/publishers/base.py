# -*- coding: utf-8 -*-
"""발행기 공통 유틸.

네이버 블로그 XML-RPC API 와 티스토리 Open API 는 모두 공식 지원이 종료되어,
발행은 Playwright 브라우저 자동화로 수행한다. 로그인 세션은 storage_state
파일로 저장해 재사용한다 (매번 로그인하면 봇 감지에 걸리기 쉽다).
"""

import os

SESSION_DIR = os.environ.get(
    "BLOG_SESSION_DIR",
    os.path.join(os.path.dirname(__file__), "..", "..", "output", "sessions"),
)


class PublishError(Exception):
    """발행 실패. message 는 UI 에 그대로 노출된다."""


def session_path(platform: str) -> str:
    os.makedirs(SESSION_DIR, exist_ok=True)
    return os.path.join(SESSION_DIR, f"{platform}_state.json")


def has_session(platform: str) -> bool:
    return os.path.exists(session_path(platform))


async def new_browser_context(playwright, platform: str, headless: bool = True):
    """저장된 로그인 세션이 있으면 복원한 컨텍스트를 연다."""
    browser = await playwright.chromium.launch(
        headless=headless,
        args=["--disable-blink-features=AutomationControlled"],
    )
    state = session_path(platform)
    context = await browser.new_context(
        storage_state=state if os.path.exists(state) else None,
        locale="ko-KR",
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        ),
    )
    return browser, context


async def save_session(context, platform: str):
    await context.storage_state(path=session_path(platform))
