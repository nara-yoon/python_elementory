"""Microsoft Clarity Data Export API 커넥터.

- 문서: https://learn.microsoft.com/clarity/setup-and-installation/clarity-data-export
- 인증: Clarity 프로젝트 설정에서 발급한 API 토큰 (Bearer)
- 제약: numOfDays 는 1~3일, 프로젝트당 하루 10회 호출 제한.
  → 매일 1회 최근 1~3일치를 수집해 로컬 DB에 누적하는 방식으로 사용한다.
- 필요한 환경변수:
    CLARITY_API_TOKEN : Data Export API 토큰
"""
from __future__ import annotations

from datetime import date, timedelta

import requests

from core import settings
from core.models import ClarityDaily

API_URL = "https://www.clarity.ms/export-data/api/v1/project-live-insights"

# Clarity 지표명 -> ClarityDaily 필드 매핑
_METRIC_FIELDS = {
    "Traffic": ("totalSessionCount", "sessions"),
    "DeadClickCount": ("sessionsWithMetricPercentage", None),  # 아래에서 개별 처리
}


class ClarityConnector:
    def __init__(self) -> None:
        self.token = settings.get("CLARITY_API_TOKEN")

    def is_configured(self) -> bool:
        return bool(self.token)

    def fetch_daily(self, num_of_days: int = 3) -> list[ClarityDaily]:
        """최근 num_of_days(1~3)일의 UX 지표를 가져온다.

        Data Export API 는 기간 합산값을 주므로, 여기서는 조회 시점 기준
        마지막 날짜 1행으로 기록한다(매일 수집해 일 단위 추이를 쌓는 용도).
        """
        if not self.is_configured():
            return []
        num_of_days = max(1, min(3, num_of_days))
        resp = requests.get(
            API_URL,
            params={"numOfDays": num_of_days},
            headers={"Authorization": f"Bearer {self.token}"},
            timeout=30,
        )
        resp.raise_for_status()
        payload = resp.json()

        row = ClarityDaily(date=date.today() - timedelta(days=1))
        for item in payload:
            name = item.get("metricName", "")
            info = (item.get("information") or [{}])[0]
            if name == "Traffic":
                row.sessions = int(float(info.get("totalSessionCount", 0)))
                row.bot_sessions = int(float(info.get("totalBotSessionCount", 0)))
            elif name == "DeadClickCount":
                row.dead_clicks = int(float(info.get("sessionsWithMetricPercentage", 0)
                                            ) / 100 * row.sessions)
            elif name == "RageClickCount":
                row.rage_clicks = int(float(info.get("sessionsWithMetricPercentage", 0)
                                            ) / 100 * row.sessions)
            elif name == "QuickbackClick":
                row.quick_backs = int(float(info.get("sessionsWithMetricPercentage", 0)
                                            ) / 100 * row.sessions)
            elif name == "ExcessiveScroll":
                row.excessive_scrolls = int(float(info.get("sessionsWithMetricPercentage", 0)
                                                  ) / 100 * row.sessions)
            elif name == "ScriptErrorCount":
                row.script_errors = int(float(info.get("sessionsWithMetricPercentage", 0)
                                              ) / 100 * row.sessions)
            elif name == "ScrollDepth":
                row.avg_scroll_depth = float(info.get("averageScrollDepth", 0))
        return [row]
