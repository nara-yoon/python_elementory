"""
Google Scholar 논문 스크래퍼
==============================
대상: https://scholar.google.com/citations?user=PhDDPiUAAAAJ
항목: 논문 제목, 인용 수, 출판 연도, 논문 링크 (최대 20개)

실행 방법:
    pip install requests beautifulsoup4
    python scholar_scraper.py
"""

import time
import sys
import requests
from bs4 import BeautifulSoup


BASE_URL = "https://scholar.google.com"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
}


def scrape_google_scholar(user_id: str, max_papers: int = 20) -> list[dict]:
    """
    Google Scholar 프로필에서 논문 정보를 스크래핑합니다.

    Args:
        user_id:    Google Scholar 사용자 ID (URL의 user= 값)
        max_papers: 수집할 최대 논문 수

    Returns:
        [{"no", "title", "citations", "year", "link"}, ...] 형태의 리스트
    """
    papers: list[dict] = []
    start = 0
    page_size = 20  # Google Scholar 한 페이지 최대

    while len(papers) < max_papers:
        url = (
            f"{BASE_URL}/citations"
            f"?user={user_id}&hl=ko&oi=ao"
            f"&cstart={start}&pagesize={page_size}&sortby=pubdate"
        )
        print(f"[요청] start={start} | 현재 수집 {len(papers)}개 ...")

        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
        except requests.exceptions.RequestException as e:
            print(f"[오류] 요청 실패: {e}")
            break

        if resp.status_code != 200:
            print(f"[오류] HTTP {resp.status_code}")
            break

        soup = BeautifulSoup(resp.text, "html.parser")
        rows = soup.select("tr.gsc_a_tr")

        if not rows:
            print("[종료] 더 이상 논문이 없습니다.")
            break

        for row in rows:
            if len(papers) >= max_papers:
                break

            # ── 제목 & 상세 링크 ──────────────────────────────────────
            title_tag = row.select_one("a.gsc_a_at")
            title = title_tag.get_text(strip=True) if title_tag else "N/A"
            href  = title_tag.get("href", "") if title_tag else ""
            link  = (BASE_URL + href) if href else "N/A"

            # ── 인용 수 ───────────────────────────────────────────────
            cited_tag = row.select_one("a.gsc_a_ac")
            citations = (cited_tag.get_text(strip=True) or "0") if cited_tag else "0"

            # ── 출판 연도 ─────────────────────────────────────────────
            year_tag = row.select_one("span.gsc_a_h.gsc_a_hc")
            year = year_tag.get_text(strip=True) if year_tag else "N/A"

            papers.append({
                "no":        len(papers) + 1,
                "title":     title,
                "citations": citations,
                "year":      year,
                "link":      link,
            })

        # 다음 페이지 여부 확인
        next_btn = soup.select_one("button#gsc_bpf_next")
        if next_btn and next_btn.has_attr("disabled"):
            print("[종료] 마지막 페이지 도달.")
            break

        start += page_size
        time.sleep(1.5)  # Google 차단 방지를 위한 딜레이

    return papers


def print_papers(papers: list[dict]) -> None:
    """수집된 논문 목록을 콘솔에 출력합니다."""
    print(f"\n{'='*70}")
    print(f"  총 {len(papers)}개 논문 수집 완료")
    print(f"{'='*70}\n")
    for p in papers:
        print(f"[{p['no']:02d}] {p['title']}")
        print(f"     Year: {p['year']:<6}  Citations: {p['citations']}")
        print(f"     Link: {p['link']}")
        print()


def save_to_csv(papers: list[dict], filename: str = "scholar_papers.csv") -> None:
    """수집된 논문 목록을 CSV 파일로 저장합니다."""
    import csv
    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["no", "title", "citations", "year", "link"])
        writer.writeheader()
        writer.writerows(papers)
    print(f"[저장] '{filename}' 파일로 저장 완료.")


if __name__ == "__main__":
    USER_ID    = "PhDDPiUAAAAJ"
    MAX_PAPERS = 20

    print(f"Google Scholar 스크래핑 시작")
    print(f"  대상: {BASE_URL}/citations?user={USER_ID}")
    print(f"  목표: {MAX_PAPERS}개 논문\n")

    papers = scrape_google_scholar(USER_ID, max_papers=MAX_PAPERS)

    if not papers:
        print("[실패] 논문을 수집하지 못했습니다.")
        sys.exit(1)

    print_papers(papers)
    save_to_csv(papers)
