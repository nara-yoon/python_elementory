"""메타(페이스북/인스타그램) 마케팅 API 커넥터.

- Graph API 직접 호출 (SDK 불필요)
- 문서: https://developers.facebook.com/docs/marketing-apis
- 필요한 환경변수:
    META_ACCESS_TOKEN   : 시스템 사용자 또는 장기 액세스 토큰
    META_AD_ACCOUNT_ID  : 광고계정 ID (숫자만, act_ 접두어 제외)
    META_PAGE_ID        : (소재 생성용) 페이스북 페이지 ID
"""
from __future__ import annotations

import json
from datetime import date

import requests

from core import settings
from core.models import (CampaignSpec, Channel, CreativeSpec, DailyMetric,
                         LaunchResult)
from .base import AdPlatformConnector, ConnectorError

GRAPH_URL = "https://graph.facebook.com/v21.0"


class MetaAdsConnector(AdPlatformConnector):
    channel = Channel.META.value

    def __init__(self) -> None:
        self.access_token = settings.get("META_ACCESS_TOKEN")
        self.account_id = settings.get("META_AD_ACCOUNT_ID")
        self.page_id = settings.get("META_PAGE_ID")

    def is_configured(self) -> bool:
        return bool(self.access_token and self.account_id)

    def _request(self, method: str, path: str, *, params: dict | None = None,
                 data: dict | None = None):
        params = dict(params or {})
        params["access_token"] = self.access_token
        resp = requests.request(method, f"{GRAPH_URL}{path}", params=params,
                                data=data, timeout=30)
        if resp.status_code >= 400:
            raise ConnectorError(f"메타 API 오류 {resp.status_code}: {resp.text[:300]}")
        return resp.json()

    def create_campaign(self, spec: CampaignSpec) -> LaunchResult:
        if not self.is_configured():
            return self._not_configured()
        try:
            act = f"/act_{self.account_id}"

            # 1) 캠페인 (트래픽 목표, 검수 전 일시중지)
            campaign = self._request("POST", f"{act}/campaigns", data={
                "name": spec.name,
                "objective": "OUTCOME_TRAFFIC",
                "status": "PAUSED",
                "special_ad_categories": "[]",
            })
            campaign_id = campaign["id"]

            # 2) 광고세트 (예산/타겟팅)
            targeting: dict = {"geo_locations": {"countries": spec.locations or ["KR"]}}
            if spec.age_min:
                targeting["age_min"] = spec.age_min
            if spec.age_max:
                targeting["age_max"] = spec.age_max
            if spec.genders:
                targeting["genders"] = [1 if g == "male" else 2 for g in spec.genders]
            adset = self._request("POST", f"{act}/adsets", data={
                "name": f"{spec.name}_세트1",
                "campaign_id": campaign_id,
                "daily_budget": spec.daily_budget,   # KRW는 최소 단위가 원
                "billing_event": "IMPRESSIONS",
                "optimization_goal": "LINK_CLICKS",
                "bid_strategy": "LOWEST_COST_WITHOUT_CAP",
                "targeting": json.dumps(targeting, ensure_ascii=False),
                "start_time": f"{spec.start_date}T00:00:00+0900",
                **({"end_time": f"{spec.end_date}T23:59:59+0900"} if spec.end_date else {}),
                "status": "PAUSED",
            })
            adset_id = adset["id"]

            # 3) 크리에이티브 + 광고
            ad_id = ""
            if self.page_id and spec.headline:
                creative = self._request("POST", f"{act}/adcreatives", data={
                    "name": f"{spec.name}_소재1",
                    "object_story_spec": json.dumps({
                        "page_id": self.page_id,
                        "link_data": {
                            "link": spec.landing_url,
                            "message": spec.description,
                            "name": spec.headline,
                            **({"picture": spec.image_url} if spec.image_url else {}),
                        },
                    }, ensure_ascii=False),
                })
                ad = self._request("POST", f"{act}/ads", data={
                    "name": f"{spec.name}_광고1",
                    "adset_id": adset_id,
                    "creative": json.dumps({"creative_id": creative["id"]}),
                    "status": "PAUSED",
                })
                ad_id = ad["id"]

            msg = "캠페인/광고세트 생성 완료 (일시중지 상태)"
            if ad_id:
                msg = "캠페인/광고세트/소재/광고 생성 완료 (일시중지 상태)"
            return LaunchResult(channel=self.channel, ok=True,
                                campaign_id=campaign_id, message=msg)
        except (ConnectorError, requests.RequestException, KeyError) as e:
            return LaunchResult(channel=self.channel, ok=False, message=str(e))

    def update_creative(self, campaign_id: str, creative: CreativeSpec) -> LaunchResult:
        """캠페인의 모든 광고세트에 새 크리에이티브 + 광고를 등록한다."""
        if not self.is_configured():
            return self._not_configured()
        if not self.page_id:
            return LaunchResult(channel=self.channel, ok=False,
                                message="META_PAGE_ID 가 필요합니다 (.env)")
        try:
            act = f"/act_{self.account_id}"
            adsets = self._request("GET", f"{act}/adsets", params={
                "campaign_id": campaign_id, "fields": "id,name", "limit": 100,
            }).get("data", [])
            if not adsets:
                return LaunchResult(channel=self.channel, ok=False,
                                    message="광고세트가 없습니다")
            new_creative = self._request("POST", f"{act}/adcreatives", data={
                "name": f"{creative.headline}_소재",
                "object_story_spec": json.dumps({
                    "page_id": self.page_id,
                    "link_data": {
                        "link": creative.landing_url,
                        "message": creative.description,
                        "name": creative.headline,
                        **({"picture": creative.image_url}
                           if creative.image_url else {}),
                    },
                }, ensure_ascii=False),
            })
            for adset in adsets:
                self._request("POST", f"{act}/ads", data={
                    "name": f"{creative.headline}_광고",
                    "adset_id": adset["id"],
                    "creative": json.dumps({"creative_id": new_creative["id"]}),
                    "status": "PAUSED",
                })
            return LaunchResult(
                channel=self.channel, ok=True, campaign_id=campaign_id,
                message=f"광고세트 {len(adsets)}개에 새 소재 등록 완료 (일시중지 상태)")
        except (ConnectorError, requests.RequestException, KeyError) as e:
            return LaunchResult(channel=self.channel, ok=False, message=str(e))

    def fetch_daily_metrics(self, start: date, end: date) -> list[DailyMetric]:
        if not self.is_configured():
            return []
        data = self._request("GET", f"/act_{self.account_id}/insights", params={
            "level": "campaign",
            "time_range": json.dumps({"since": start.isoformat(),
                                      "until": end.isoformat()}),
            "time_increment": 1,
            "fields": ("campaign_id,campaign_name,impressions,clicks,spend,"
                       "actions,action_values"),
            "limit": 500,
        })
        out: list[DailyMetric] = []
        rows = data.get("data", [])
        while True:
            for row in rows:
                conversions = sum(
                    float(a["value"]) for a in row.get("actions", [])
                    if a.get("action_type") in ("purchase", "omni_purchase"))
                revenue = sum(
                    float(a["value"]) for a in row.get("action_values", [])
                    if a.get("action_type") in ("purchase", "omni_purchase"))
                out.append(DailyMetric(
                    date=date.fromisoformat(row["date_start"]),
                    channel=self.channel,
                    campaign_id=row.get("campaign_id", ""),
                    campaign_name=row.get("campaign_name", ""),
                    impressions=int(row.get("impressions", 0)),
                    clicks=int(row.get("clicks", 0)),
                    cost=float(row.get("spend", 0)),
                    conversions=conversions,
                    revenue=revenue,
                ))
            next_url = data.get("paging", {}).get("next")
            if not next_url:
                break
            resp = requests.get(next_url, timeout=30)
            if resp.status_code >= 400:
                break
            data = resp.json()
            rows = data.get("data", [])
        return out
