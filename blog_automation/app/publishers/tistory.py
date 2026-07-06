# -*- coding: utf-8 -*-
"""티스토리 발행기 (Playwright).

티스토리 Open API 는 2024년 2월 종료되어 브라우저 자동화로 발행한다.
티스토리 글쓰기 에디터는 HTML 모드를 지원하므로, 생성된 HTML 을
그대로 주입할 수 있어 서식(형광펜/볼드/인용구)이 온전히 유지된다.

필요 환경변수
- TISTORY_BLOG   : 블로그 이름 (https://{TISTORY_BLOG}.tistory.com)
- KAKAO_ID / KAKAO_PW : 카카오 계정 (세션이 없을 때 자동 로그인 시도)
"""

import asyncio
import os

from .base import PublishError, has_session, new_browser_context, save_session

LOGIN_URL = "https://www.tistory.com/auth/login"


def _newpost_url(blog: str) -> str:
    return f"https://{blog}.tistory.com/manage/newpost/?type=post"


async def _login(page, context):
    kakao_id = os.environ.get("KAKAO_ID")
    kakao_pw = os.environ.get("KAKAO_PW")
    if not kakao_id or not kakao_pw:
        raise PublishError(
            "티스토리 로그인 세션이 없습니다. .env 에 KAKAO_ID/KAKAO_PW 를 설정하거나 "
            "`python -m app.publishers.tistory` 로 수동 로그인 세션을 먼저 만들어 주세요."
        )
    await page.goto(LOGIN_URL)
    await page.click("a.btn_login.link_kakao_id, .link_kakao_id")
    await page.wait_for_load_state("networkidle")
    await page.fill('input[name="loginId"]', kakao_id)
    await page.fill('input[name="password"]', kakao_pw)
    await page.click('button[type="submit"]')
    await page.wait_for_load_state("networkidle")

    if "accounts.kakao.com" in page.url:
        raise PublishError(
            "카카오 로그인에 실패했습니다 (2단계 인증 등). "
            "`python -m app.publishers.tistory` 를 실행해 직접 로그인해 주세요."
        )
    await save_session(context, "tistory")


async def publish(title: str, html: str, tags: list, headless: bool = True) -> dict:
    blog = os.environ.get("TISTORY_BLOG")
    if not blog:
        raise PublishError(".env 에 TISTORY_BLOG (블로그 이름) 을 설정해 주세요.")

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        raise PublishError(
            "playwright 가 설치되어 있지 않습니다. "
            "`pip install playwright && playwright install chromium` 을 실행해 주세요."
        )

    async with async_playwright() as p:
        browser, context = await new_browser_context(p, "tistory", headless=headless)
        try:
            page = await context.new_page()

            if not has_session("tistory"):
                await _login(page, context)

            await page.goto(_newpost_url(blog))
            await page.wait_for_load_state("networkidle")
            if "auth/login" in page.url or "accounts.kakao.com" in page.url:
                await _login(page, context)
                await page.goto(_newpost_url(blog))
                await page.wait_for_load_state("networkidle")

            # 임시저장 글 복구 알림 무시
            page.on("dialog", lambda dialog: asyncio.ensure_future(dialog.dismiss()))
            await asyncio.sleep(1.5)

            # 제목 입력
            await page.fill("#post-title-inp, textarea.textarea_tit", title)

            # 에디터를 HTML(마크다운 아님) 모드로 전환한 뒤 본문 주입
            await page.click("#editor-mode-layer-btn-open, .btn_editor_mode")
            await page.click("#editor-mode-html, #editor-mode-html-text")
            await asyncio.sleep(0.8)

            # HTML 모드는 CodeMirror 기반 — API 로 직접 주입
            injected = await page.evaluate(
                """(html) => {
                    const cmEl = document.querySelector('.CodeMirror');
                    if (cmEl && cmEl.CodeMirror) {
                        cmEl.CodeMirror.setValue(html);
                        return true;
                    }
                    return false;
                }""",
                html,
            )
            if not injected:
                raise PublishError("티스토리 HTML 에디터를 찾지 못했습니다 (UI 변경 가능성).")

            # 태그 입력
            tag_input = page.locator("input.tf_g, #tagText")
            if await tag_input.count():
                for tag in (tags or [])[:10]:
                    await tag_input.first.fill(tag)
                    await page.keyboard.press("Enter")

            # 완료 → 공개 발행
            await page.click("#publish-layer-btn, .btn_publish")
            await asyncio.sleep(0.8)
            open_radio = page.locator("#open20")  # 공개
            if await open_radio.count():
                await open_radio.check()
            await page.click("#publish-btn, .btn_apply")
            await page.wait_for_load_state("networkidle")

            await save_session(context, "tistory")
            return {"platform": "tistory", "url": page.url, "status": "published"}
        except PublishError:
            raise
        except Exception as exc:
            raise PublishError(
                f"티스토리 발행 중 오류가 발생했습니다: {exc}. 에디터 UI 가 변경되었을 수 "
                "있으니 '복사용 HTML' 로 수동 붙여넣기를 이용해 주세요."
            )
        finally:
            await browser.close()


async def login_interactive():
    """headless=False 브라우저를 띄워 사람이 직접 로그인 → 세션 저장."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser, context = await new_browser_context(p, "tistory", headless=False)
        page = await context.new_page()
        await page.goto(LOGIN_URL)
        print("브라우저에서 티스토리(카카오)에 로그인해 주세요.")
        await page.wait_for_url("https://www.tistory.com/**", timeout=300_000)
        await save_session(context, "tistory")
        await browser.close()
        print("티스토리 로그인 세션이 저장되었습니다.")


if __name__ == "__main__":
    asyncio.run(login_interactive())
