"""네이버 GFA(성과형 디스플레이광고) API 커넥터.

- GFA API 는 네이버와 제휴된 광고주/대행사에게만 열려 있는 폐쇄형 API 다.
  사용 승인 후 발급받는 문서의 엔드포인트/스키마에 맞춰 아래 상수만 수정하면 된다.
- 인증: OAuth2 Bearer 토큰
- 필요한 환경변수:
    NAVER_GFA_ACCESS_TOKEN : 발급받은 액세스 토큰
    NAVER_GFA_ACCOUNT_NO   : 광고계정 번호
    NAVER_GFA_BASE_URL     : (선택) 승인 문서에 안내된 베이스 URL
"""
from __future__ import annotations

from datetime import date

import requests

from core import settings
from core.models import (CampaignSpec, Channel, CreativeSpec, DailyMetric,
                         LaunchResult)
from .base import AdPlatformConnector, ConnectorError

DEFAULT_BASE_URL = "https://openapi.gfa.naver.com/v1"


class NaverGfaConnector(AdPlatformConnector):
    channel = Channel.NAVER_GFA.value

    def __init__(self) -> None:
        self.access_token = settings.get("NAVER_GFA_ACCESS_TOKEN")
        self.account_no = settings.get("NAVER_GFA_ACCOUNT_NO")
        self.base_url = settings.get("NAVER_GFA_BASE_URL", DEFAULT_BASE_URL)

    def is_configured(self) -> bool:
        return bool(self.access_token and self.account_no)

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    def _request(self, method: str, path: str, **kwargs):
        resp = requests.request(
            method, f"{self.base_url}{path}", headers=self._headers(),
            timeout=30, **kwargs,
        )
        if resp.status_code >= 400:
            raise ConnectorError(f"네이버 GFA API 오류 {resp.status_code}: {resp.text[:300]}")
        return resp.json() if resp.text else None

    def create_campaign(self, spec: CampaignSpec) -> LaunchResult:
        if not self.is_configured():
            return self._not_configured()
        try:
            payload = {
                "accountNo": self.account_no,
                "name": spec.name,
                "objective": "WEB_SITE_TRAFFIC",
                "dailyBudget": spec.daily_budget,
                "startDate": spec.start_date,
                "endDate": spec.end_date,
                "landingUrl": spec.landing_url,
                "creative": {
                    "title": spec.headline,
                    "description": spec.description,
                    "imageUrl": spec.image_url,
                },
                "targeting": {
                    "ageMin": spec.age_min,
                    "ageMax": spec.age_max,
                    "genders": spec.genders or None,
                    "regions": spec.locations or ["KR"],
                },
            }
            data = self._request("POST", "/campaigns", json=payload)
            return LaunchResult(channel=self.channel, ok=True,
                                campaign_id=str(data.get("campaignNo", "")),
                                message="GFA 캠페인 생성 완료")
        except (ConnectorError, requests.RequestException) as e:
            return LaunchResult(channel=self.channel, ok=False, message=str(e))

    def update_creative(self, campaign_id: str, creative: CreativeSpec) -> LaunchResult:
        """캠페인에 새 소재를 등록한다 (GFA 승인 문서의 스키마에 맞춰 조정)."""
        if not self.is_configured():
            return self._not_configured()
        try:
            self._request("POST", f"/campaigns/{campaign_id}/creatives", json={
                "accountNo": self.account_no,
                "title": creative.headline,
                "description": creative.description,
                "imageUrl": creative.image_url,
                "landingUrl": creative.landing_url,
            })
            return LaunchResult(channel=self.channel, ok=True, campaign_id=campaign_id,
                                message="새 소재 등록 완료")
        except (ConnectorError, requests.RequestException) as e:
            return LaunchResult(channel=self.channel, ok=False, message=str(e))

    def fetch_daily_metrics(self, start: date, end: date) -> list[DailyMetric]:
        if not self.is_configured():
            return []
        data = self._request("GET", "/report/campaigns", params={
            "accountNo": self.account_no,
            "startDate": start.isoformat(),
            "endDate": end.isoformat(),
            "timeUnit": "DAY",
        })
        out: list[DailyMetric] = []
        for row in (data or {}).get("rows", []):
            out.append(DailyMetric(
                date=date.fromisoformat(row["date"]),
                channel=self.channel,
                campaign_id=str(row.get("campaignNo", "")),
                campaign_name=row.get("campaignName", ""),
                impressions=int(row.get("impressions", 0)),
                clicks=int(row.get("clicks", 0)),
                cost=float(row.get("cost", 0)),
                conversions=float(row.get("conversions", 0)),
                revenue=float(row.get("conversionValue", 0)),
            ))
        return out
