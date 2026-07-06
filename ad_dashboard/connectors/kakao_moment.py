"""카카오모먼트(디스플레이광고) API 커넥터.

- 문서: https://developers.kakao.com (카카오모먼트 API)
- 인증: 카카오 OAuth2 액세스 토큰 + adAccountId 헤더
- 필요한 환경변수:
    KAKAO_ACCESS_TOKEN       : OAuth2 액세스 토큰 (키워드광고와 공용)
    KAKAO_MOMENT_AD_ACCOUNT  : 모먼트 광고계정 ID
"""
from __future__ import annotations

from datetime import date

import requests

from core import settings
from core.models import (CampaignSpec, Channel, CreativeSpec, DailyMetric,
                         LaunchResult)
from .base import AdPlatformConnector, ConnectorError

BASE_URL = "https://apis.moment.kakao.com"


class KakaoMomentConnector(AdPlatformConnector):
    channel = Channel.KAKAO_MOMENT.value

    def __init__(self) -> None:
        self.access_token = settings.get("KAKAO_ACCESS_TOKEN")
        self.ad_account_id = settings.get("KAKAO_MOMENT_AD_ACCOUNT")

    def is_configured(self) -> bool:
        return bool(self.access_token and self.ad_account_id)

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "adAccountId": self.ad_account_id,
            "Content-Type": "application/json",
        }

    def _request(self, method: str, path: str, **kwargs):
        resp = requests.request(method, BASE_URL + path, headers=self._headers(),
                                timeout=30, **kwargs)
        if resp.status_code >= 400:
            raise ConnectorError(f"카카오모먼트 API 오류 {resp.status_code}: {resp.text[:300]}")
        return resp.json() if resp.text else None

    def create_campaign(self, spec: CampaignSpec) -> LaunchResult:
        if not self.is_configured():
            return self._not_configured()
        try:
            campaign = self._request("POST", "/openapi/v4/campaigns", json={
                "name": spec.name,
                "objective": {"type": "VISITING"},          # 방문 목표
                "dailyBudgetAmount": spec.daily_budget,
            })
            campaign_id = str(campaign["id"])

            adgroup = self._request("POST", "/openapi/v4/adGroups", json={
                "campaignId": campaign_id,
                "name": f"{spec.name}_그룹1",
                "pricingType": "CPC",
                "bidAmount": 200,
                "dailyBudgetAmount": spec.daily_budget,
                "targeting": {
                    "age": ([f"{a}" for a in range(spec.age_min or 20,
                                                   (spec.age_max or 59) + 1, 5)]
                            if spec.age_min else None),
                    "gender": spec.genders or None,
                    "location": spec.locations or None,
                },
                "schedule": {"beginDate": spec.start_date.replace("-", ""),
                             "endDate": (spec.end_date or "").replace("-", "") or None},
            })
            adgroup_id = str(adgroup["id"])

            if spec.image_url:
                self._request("POST", "/openapi/v4/creatives", json={
                    "adGroupId": adgroup_id,
                    "format": "IMAGE_NATIVE",
                    "title": spec.headline,
                    "description": spec.description,
                    "landingUrl": spec.landing_url,
                    "image": {"url": spec.image_url},
                })
            return LaunchResult(channel=self.channel, ok=True, campaign_id=campaign_id,
                                message="캠페인/그룹/소재 생성 완료")
        except (ConnectorError, requests.RequestException, KeyError) as e:
            return LaunchResult(channel=self.channel, ok=False, message=str(e))

    def update_creative(self, campaign_id: str, creative: CreativeSpec) -> LaunchResult:
        """캠페인의 모든 광고그룹에 새 이미지 소재를 등록한다."""
        if not self.is_configured():
            return self._not_configured()
        try:
            adgroups = self._request("GET", "/openapi/v4/adGroups",
                                     params={"campaignId": campaign_id}) or {}
            content = adgroups.get("content",
                                   adgroups if isinstance(adgroups, list) else [])
            if not content:
                return LaunchResult(channel=self.channel, ok=False,
                                    message="광고그룹이 없습니다")
            for g in content:
                self._request("POST", "/openapi/v4/creatives", json={
                    "adGroupId": str(g["id"]),
                    "format": "IMAGE_NATIVE",
                    "title": creative.headline,
                    "description": creative.description,
                    "landingUrl": creative.landing_url,
                    "image": {"url": creative.image_url},
                })
            return LaunchResult(
                channel=self.channel, ok=True, campaign_id=campaign_id,
                message=f"광고그룹 {len(content)}개에 새 소재 등록 완료")
        except (ConnectorError, requests.RequestException, KeyError) as e:
            return LaunchResult(channel=self.channel, ok=False, message=str(e))

    def fetch_daily_metrics(self, start: date, end: date) -> list[DailyMetric]:
        if not self.is_configured():
            return []
        campaigns = self._request("GET", "/openapi/v4/campaigns") or {}
        content = campaigns.get("content", campaigns if isinstance(campaigns, list) else [])
        out: list[DailyMetric] = []
        for c in content:
            cid, cname = str(c["id"]), c.get("name", "")
            report = self._request("GET", "/openapi/v4/campaigns/report", params={
                "campaignId": cid,
                "start": start.strftime("%Y%m%d"),
                "end": end.strftime("%Y%m%d"),
                "timeUnit": "DAY",
                "metricsGroup": "BASIC,PIXEL_SDK_CONVERSION",
            })
            for row in (report or {}).get("data", []):
                metrics = row.get("metrics", {})
                dimensions = row.get("dimensions", {})
                out.append(DailyMetric(
                    date=date.fromisoformat(str(dimensions.get("start", row.get("start")))[:10]),
                    channel=self.channel, campaign_id=cid, campaign_name=cname,
                    impressions=int(metrics.get("imp", 0)),
                    clicks=int(metrics.get("click", 0)),
                    cost=float(metrics.get("cost", 0)),
                    conversions=float(metrics.get("convPurchase1d", 0)),
                    revenue=float(metrics.get("convPurchaseP1d", 0)),
                ))
        return out
