# -*- coding: utf-8 -*-
"""네이버 블로그 발행기 (Playwright).

네이버는 공식 글쓰기 API 를 제공하지 않으므로 스마트에디터 ONE 을
브라우저 자동화로 조작한다.

동작 방식
1. 저장된 세션(storage_state)이 있으면 바로 글쓰기 페이지로 이동.
2. 세션이 없으면 NAVER_ID / NAVER_PW 로 로그인 시도.
   - 네이버는 자동 입력을 감지하므로 캡차가 뜨면 실패 처리하고,
     `login_interactive()` (headless=False) 로 사람이 직접 로그인해
     세션을 만들어 두는 방식을 권장한다.
3. 제목 입력 → 본문은 클립보드 HTML 붙여넣기 대신 블록 단위 키 입력으로 작성.
"""

import asyncio
import os

from .base import PublishError, has_session, new_browser_context, save_session

WRITE_URL = "https://blog.naver.com/{blog_id}?Redirect=Write&"
LOGIN_URL = "https://nid.naver.com/nidlogin.login"


async def _login(page, context):
    naver_id = os.environ.get("NAVER_ID")
    naver_pw = os.environ.get("NAVER_PW")
    if not naver_id or not naver_pw:
        raise PublishError(
            "네이버 로그인 세션이 없습니다. .env 에 NAVER_ID/NAVER_PW 를 설정하거나 "
            "`python -m app.publishers.naver` 로 수동 로그인 세션을 먼저 만들어 주세요."
        )
    await page.goto(LOGIN_URL)
    # 봇 감지를 피하기 위해 JS 로 값을 주입한 뒤 input 이벤트를 발생시킨다
    await page.evaluate(
        """([id, pw]) => {
            const setValue = (selector, value) => {
                const el = document.querySelector(selector);
                el.value = value;
                el.dispatchEvent(new Event('input', { bubbles: true }));
            };
            setValue('#id', id);
            setValue('#pw', pw);
        }""",
        [naver_id, naver_pw],
    )
    await asyncio.sleep(1.0)
    await page.click("#log\\.login")
    await page.wait_for_load_state("networkidle")

    if "nidlogin" in page.url:
        raise PublishError(
            "네이버 로그인에 실패했습니다 (캡차 또는 2단계 인증). "
            "`python -m app.publishers.naver` 를 실행해 브라우저에서 직접 로그인해 "
            "세션을 저장한 뒤 다시 시도해 주세요."
        )
    await save_session(context, "naver")


async def _type_blocks(page, blocks: list):
    """스마트에디터 ONE 본문 영역에 블록을 순서대로 입력한다."""
    body = page.locator(".se-component-content p.se-text-paragraph").first
    await body.click()

    for block in blocks:
        btype = block.get("type")
        text = (block.get("text") or "").strip()

        if btype == "heading" and text:
            await page.keyboard.type(text)
            # 입력한 줄을 선택해 소제목(굵은 큰 글씨) 서식 적용
            await page.keyboard.press("Shift+Home")
            await page.keyboard.press("Control+B")
            await page.keyboard.press("End")
            await page.keyboard.press("Enter")
        elif btype == "quote" and text:
            await page.keyboard.type(f"❝ {text} ❞")
            await page.keyboard.press("Enter")
        elif btype == "divider":
            await page.keyboard.type("─" * 20)
            await page.keyboard.press("Enter")
        elif btype == "image":
            src = block.get("src", "")
            if src and os.path.exists(src):
                async with page.expect_file_chooser() as chooser_info:
                    await page.click("button.se-image-toolbar-button")
                chooser = await chooser_info.value
                await chooser.set_files(src)
                await asyncio.sleep(2.5)  # 업로드 대기
                await page.keyboard.press("Escape")
        elif text:
            await page.keyboard.type(text)
            await page.keyboard.press("Enter")
        await page.keyboard.press("Enter")


async def publish(title: str, blocks: list, tags: list, headless: bool = True) -> dict:
    blog_id = os.environ.get("NAVER_BLOG_ID") or os.environ.get("NAVER_ID")
    if not blog_id:
        raise PublishError(".env 에 NAVER_BLOG_ID (또는 NAVER_ID) 를 설정해 주세요.")

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        raise PublishError(
            "playwright 가 설치되어 있지 않습니다. "
            "`pip install playwright && playwright install chromium` 을 실행해 주세요."
        )

    async with async_playwright() as p:
        browser, context = await new_browser_context(p, "naver", headless=headless)
        try:
            page = await context.new_page()

            if not has_session("naver"):
                await _login(page, context)

            await page.goto(WRITE_URL.format(blog_id=blog_id))
            await page.wait_for_load_state("networkidle")

            # 글쓰기 화면은 mainFrame iframe 안에 있다
            frame = page.frame(name="mainFrame") or page

            # 이전 작성 글 복구 팝업 닫기
            cancel = frame.locator(".se-popup-button-cancel")
            if await cancel.count():
                await cancel.first.click()

            # 도움말 패널 닫기
            help_close = frame.locator(".se-help-panel-close-button")
            if await help_close.count():
                await help_close.first.click()

            title_area = frame.locator(".se-section-documentTitle .se-text-paragraph").first
            await title_area.click()
            await page.keyboard.type(title)
            await page.keyboard.press("Enter")

            await _type_blocks(frame if frame is not page else page, blocks)

            # 발행 버튼 → 태그 입력 → 최종 발행
            await frame.locator("button.publish_btn__m9KHH, [class*='publish_btn']").first.click()
            tag_input = frame.locator("#tag-input, [class*='tag_input']")
            if await tag_input.count():
                for tag in (tags or [])[:10]:
                    await tag_input.first.fill(tag)
                    await page.keyboard.press("Enter")
            await frame.locator(
                "[class*='confirm_btn'], button[data-testid='seOnePublishBtn']"
            ).first.click()
            await page.wait_for_load_state("networkidle")

            await save_session(context, "naver")
            return {"platform": "naver", "url": page.url, "status": "published"}
        except PublishError:
            raise
        except Exception as exc:
            raise PublishError(
                f"네이버 발행 중 오류가 발생했습니다: {exc}. 에디터 UI 가 변경되었을 수 "
                "있으니 '복사용 HTML' 로 수동 붙여넣기를 이용해 주세요."
            )
        finally:
            await browser.close()


async def login_interactive():
    """headless=False 브라우저를 띄워 사람이 직접 로그인 → 세션 저장."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser, context = await new_browser_context(p, "naver", headless=False)
        page = await context.new_page()
        await page.goto(LOGIN_URL)
        print("브라우저에서 네이버에 로그인해 주세요. 로그인이 끝나면 자동으로 저장됩니다.")
        await page.wait_for_url("https://www.naver.com/**", timeout=300_000)
        await save_session(context, "naver")
        await browser.close()
        print("네이버 로그인 세션이 저장되었습니다.")


if __name__ == "__main__":
    asyncio.run(login_interactive())
