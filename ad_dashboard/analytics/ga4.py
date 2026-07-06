"""GA4 (Google Analytics 4) Data API 커넥터.

- 라이브러리: google-analytics-data (pip install google-analytics-data)
- 인증: 서비스 계정 JSON 키 (GA4 속성에 뷰어 이상 권한 부여 필요)
- 필요한 환경변수:
    GA4_PROPERTY_ID              : GA4 속성 ID (숫자)
    GOOGLE_APPLICATION_CREDENTIALS : 서비스 계정 키 JSON 파일 경로
"""
from __future__ import annotations

from datetime import date

from core import settings
from core.models import Ga4Daily


class Ga4Connector:
    def __init__(self) -> None:
        self.property_id = settings.get("GA4_PROPERTY_ID")
        self.credentials_path = settings.get("GOOGLE_APPLICATION_CREDENTIALS")

    def is_configured(self) -> bool:
        return bool(self.property_id and self.credentials_path)

    def fetch_daily(self, start: date, end: date) -> list[Ga4Daily]:
        """일자 x 소스/매체별 세션·전환·매출을 가져온다."""
        if not self.is_configured():
            return []
        from google.analytics.data_v1beta import BetaAnalyticsDataClient
        from google.analytics.data_v1beta.types import (
            DateRange, Dimension, Metric, RunReportRequest,
        )

        client = BetaAnalyticsDataClient()
        request = RunReportRequest(
            property=f"properties/{self.property_id}",
            date_ranges=[DateRange(start_date=start.isoformat(),
                                   end_date=end.isoformat())],
            dimensions=[Dimension(name="date"),
                        Dimension(name="sessionSourceMedium")],
            metrics=[Metric(name="sessions"),
                     Metric(name="engagedSessions"),
                     Metric(name="conversions"),
                     Metric(name="totalRevenue"),
                     Metric(name="userEngagementDuration")],
            limit=100000,
        )
        response = client.run_report(request)
        out: list[Ga4Daily] = []
        for row in response.rows:
            d = row.dimension_values[0].value          # YYYYMMDD
            sessions = int(float(row.metric_values[0].value or 0))
            engagement_total = float(row.metric_values[4].value or 0)
            out.append(Ga4Daily(
                date=date(int(d[:4]), int(d[4:6]), int(d[6:8])),
                source_medium=row.dimension_values[1].value,
                sessions=sessions,
                engaged_sessions=int(float(row.metric_values[1].value or 0)),
                conversions=float(row.metric_values[2].value or 0),
                revenue=float(row.metric_values[3].value or 0),
                avg_engagement_seconds=(engagement_total / sessions if sessions else 0),
            ))
        return out
