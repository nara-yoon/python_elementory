"""구글 애즈 API 커넥터 (검색 캠페인 + GDN 디스플레이 캠페인).

- 공식 파이썬 라이브러리 `google-ads` 사용 (pip install google-ads)
- 인증: OAuth2 리프레시 토큰 + 개발자 토큰 (google-ads.yaml 또는 환경변수)
- 필요한 환경변수:
    GOOGLE_ADS_DEVELOPER_TOKEN
    GOOGLE_ADS_CLIENT_ID
    GOOGLE_ADS_CLIENT_SECRET
    GOOGLE_ADS_REFRESH_TOKEN
    GOOGLE_ADS_CUSTOMER_ID        : 하이픈 없는 10자리 (예: 1234567890)
    GOOGLE_ADS_LOGIN_CUSTOMER_ID  : (선택) MCC 계정 ID

하나의 커넥터 클래스가 network 인자("SEARCH" | "DISPLAY")에 따라
구글 검색광고와 GDN 을 각각 담당한다.
"""
from __future__ import annotations

from datetime import date

from core import settings
from core.models import (CampaignSpec, Channel, CreativeSpec, DailyMetric,
                         LaunchResult)
from .base import AdPlatformConnector, ConnectorError

_REQUIRED = (
    "GOOGLE_ADS_DEVELOPER_TOKEN", "GOOGLE_ADS_CLIENT_ID",
    "GOOGLE_ADS_CLIENT_SECRET", "GOOGLE_ADS_REFRESH_TOKEN",
    "GOOGLE_ADS_CUSTOMER_ID",
)


class GoogleAdsConnector(AdPlatformConnector):
    def __init__(self, network: str = "SEARCH") -> None:
        assert network in ("SEARCH", "DISPLAY")
        self.network = network
        self.channel = (Channel.GOOGLE_SEARCH.value if network == "SEARCH"
                        else Channel.GOOGLE_GDN.value)
        self.customer_id = settings.get("GOOGLE_ADS_CUSTOMER_ID")

    def is_configured(self) -> bool:
        return settings.has_all(*_REQUIRED)

    def _client(self):
        try:
            from google.ads.googleads.client import GoogleAdsClient
        except ImportError as e:
            raise ConnectorError(
                "google-ads 패키지가 없습니다: pip install google-ads"
            ) from e
        config = {
            "developer_token": settings.get("GOOGLE_ADS_DEVELOPER_TOKEN"),
            "client_id": settings.get("GOOGLE_ADS_CLIENT_ID"),
            "client_secret": settings.get("GOOGLE_ADS_CLIENT_SECRET"),
            "refresh_token": settings.get("GOOGLE_ADS_REFRESH_TOKEN"),
            "use_proto_plus": True,
        }
        login_cid = settings.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID")
        if login_cid:
            config["login_customer_id"] = login_cid
        return GoogleAdsClient.load_from_dict(config)

    # -- 캠페인 생성 ---------------------------------------------------------
    def create_campaign(self, spec: CampaignSpec) -> LaunchResult:
        if not self.is_configured():
            return self._not_configured()
        try:
            client = self._client()

            # 1) 캠페인 예산
            budget_svc = client.get_service("CampaignBudgetService")
            budget_op = client.get_type("CampaignBudgetOperation")
            budget = budget_op.create
            budget.name = f"{spec.name} 예산 ({self.network})"
            budget.amount_micros = spec.daily_budget * 1_000_000  # KRW -> micros
            budget.delivery_method = client.enums.BudgetDeliveryMethodEnum.STANDARD
            budget_resp = budget_svc.mutate_campaign_budgets(
                customer_id=self.customer_id, operations=[budget_op])
            budget_resource = budget_resp.results[0].resource_name

            # 2) 캠페인 (검색 or 디스플레이)
            campaign_svc = client.get_service("CampaignService")
            campaign_op = client.get_type("CampaignOperation")
            campaign = campaign_op.create
            campaign.name = f"{spec.name} ({'검색' if self.network == 'SEARCH' else 'GDN'})"
            channel_enum = client.enums.AdvertisingChannelTypeEnum
            campaign.advertising_channel_type = (
                channel_enum.SEARCH if self.network == "SEARCH" else channel_enum.DISPLAY)
            campaign.status = client.enums.CampaignStatusEnum.PAUSED  # 검수 후 직접 활성화
            campaign.campaign_budget = budget_resource
            campaign.manual_cpc.enhanced_cpc_enabled = False
            campaign.start_date = spec.start_date.replace("-", "")
            if spec.end_date:
                campaign.end_date = spec.end_date.replace("-", "")
            campaign_resp = campaign_svc.mutate_campaigns(
                customer_id=self.customer_id, operations=[campaign_op])
            campaign_resource = campaign_resp.results[0].resource_name
            campaign_id = campaign_resource.split("/")[-1]

            # 3) 광고그룹
            adgroup_svc = client.get_service("AdGroupService")
            adgroup_op = client.get_type("AdGroupOperation")
            adgroup = adgroup_op.create
            adgroup.name = f"{spec.name}_그룹1"
            adgroup.campaign = campaign_resource
            adgroup.cpc_bid_micros = 300 * 1_000_000
            adgroup_resp = adgroup_svc.mutate_ad_groups(
                customer_id=self.customer_id, operations=[adgroup_op])
            adgroup_resource = adgroup_resp.results[0].resource_name

            # 4) 검색 캠페인이면 키워드 등록
            if self.network == "SEARCH" and spec.keywords:
                criterion_svc = client.get_service("AdGroupCriterionService")
                ops = []
                for kw in spec.keywords[:100]:
                    op = client.get_type("AdGroupCriterionOperation")
                    criterion = op.create
                    criterion.ad_group = adgroup_resource
                    criterion.keyword.text = kw
                    criterion.keyword.match_type = client.enums.KeywordMatchTypeEnum.PHRASE
                    ops.append(op)
                criterion_svc.mutate_ad_group_criteria(
                    customer_id=self.customer_id, operations=ops)

            return LaunchResult(
                channel=self.channel, ok=True, campaign_id=campaign_id,
                message="캠페인 생성 완료 (일시중지 상태 — 소재 등록 후 활성화하세요)")
        except ConnectorError as e:
            return LaunchResult(channel=self.channel, ok=False, message=str(e))
        except Exception as e:  # GoogleAdsException 포함
            return LaunchResult(channel=self.channel, ok=False, message=str(e)[:500])

    # -- 소재 변경 -----------------------------------------------------------
    def update_creative(self, campaign_id: str, creative: CreativeSpec) -> LaunchResult:
        """검색 캠페인의 모든 광고그룹에 새 반응형 검색광고(RSA)를 등록한다.

        GDN 반응형 디스플레이 광고는 이미지 에셋 업로드가 선행돼야 하므로
        여기서는 지원하지 않는다(구글 애즈 관리자에서 교체 권장).
        """
        if not self.is_configured():
            return self._not_configured()
        if self.network != "SEARCH":
            return LaunchResult(
                channel=self.channel, ok=False,
                message="GDN 소재는 이미지 에셋 업로드가 필요해 API 일괄 변경을 "
                        "지원하지 않습니다. 구글 애즈 관리자에서 교체하세요.")
        try:
            client = self._client()
            ga_service = client.get_service("GoogleAdsService")
            rows = ga_service.search(
                customer_id=self.customer_id,
                query=f"""SELECT ad_group.resource_name FROM ad_group
                          WHERE campaign.id = {campaign_id}
                            AND ad_group.status != 'REMOVED'""")
            adgroup_resources = [r.ad_group.resource_name for r in rows]
            if not adgroup_resources:
                return LaunchResult(channel=self.channel, ok=False,
                                    message="광고그룹이 없습니다")
            ad_svc = client.get_service("AdGroupAdService")
            ops = []
            for resource in adgroup_resources:
                op = client.get_type("AdGroupAdOperation")
                ad_group_ad = op.create
                ad_group_ad.ad_group = resource
                ad_group_ad.status = client.enums.AdGroupAdStatusEnum.PAUSED
                rsa = ad_group_ad.ad.responsive_search_ad
                for text in (creative.headline[:30], creative.headline[:30] + " 안내",
                             "공식 홈페이지"):
                    h = client.get_type("AdTextAsset")
                    h.text = text[:30]
                    rsa.headlines.append(h)
                for text in (creative.description[:90], "지금 바로 확인하세요"):
                    d = client.get_type("AdTextAsset")
                    d.text = text[:90]
                    rsa.descriptions.append(d)
                ad_group_ad.ad.final_urls.append(creative.landing_url)
                ops.append(op)
            ad_svc.mutate_ad_group_ads(customer_id=self.customer_id, operations=ops)
            return LaunchResult(
                channel=self.channel, ok=True, campaign_id=campaign_id,
                message=f"광고그룹 {len(ops)}개에 새 RSA 등록 완료 (일시중지 상태)")
        except ConnectorError as e:
            return LaunchResult(channel=self.channel, ok=False, message=str(e))
        except Exception as e:
            return LaunchResult(channel=self.channel, ok=False, message=str(e)[:500])

    # -- 성과 수집 -----------------------------------------------------------
    def fetch_daily_metrics(self, start: date, end: date) -> list[DailyMetric]:
        if not self.is_configured():
            return []
        client = self._client()
        ga_service = client.get_service("GoogleAdsService")
        network_filter = ("SEARCH" if self.network == "SEARCH" else "DISPLAY")
        query = f"""
            SELECT
              segments.date,
              campaign.id,
              campaign.name,
              metrics.impressions,
              metrics.clicks,
              metrics.cost_micros,
              metrics.conversions,
              metrics.conversions_value
            FROM campaign
            WHERE segments.date BETWEEN '{start.isoformat()}' AND '{end.isoformat()}'
              AND campaign.advertising_channel_type = '{network_filter}'
        """
        out: list[DailyMetric] = []
        for batch in ga_service.search_stream(customer_id=self.customer_id, query=query):
            for row in batch.results:
                out.append(DailyMetric(
                    date=date.fromisoformat(row.segments.date),
                    channel=self.channel,
                    campaign_id=str(row.campaign.id),
                    campaign_name=row.campaign.name,
                    impressions=int(row.metrics.impressions),
                    clicks=int(row.metrics.clicks),
                    cost=row.metrics.cost_micros / 1_000_000,
                    conversions=float(row.metrics.conversions),
                    revenue=float(row.metrics.conversions_value),
                ))
        return out
