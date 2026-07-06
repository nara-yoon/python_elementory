"""통합 데이터 모델.

모든 광고 플랫폼의 성과 데이터를 하나의 공통 스키마로 정규화한다.
플랫폼별 커넥터는 각자의 API 응답을 이 모델로 변환해서 반환해야 한다.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import date
from enum import Enum


class Channel(str, Enum):
    """광고 채널. 값은 DB/차트에서 그대로 식별자로 쓰인다."""

    NAVER_SEARCH = "naver_search"      # 네이버 검색광고 (파워링크 등)
    NAVER_GFA = "naver_gfa"            # 네이버 성과형 디스플레이광고 (GFA)
    KAKAO_SEARCH = "kakao_search"      # 카카오 키워드광고
    KAKAO_MOMENT = "kakao_moment"      # 카카오모먼트 (디스플레이)
    GOOGLE_SEARCH = "google_search"    # 구글 검색광고
    GOOGLE_GDN = "google_gdn"          # 구글 디스플레이 네트워크
    META = "meta"                      # 메타 (페이스북/인스타그램)


# 대시보드 표기용 한글 이름
CHANNEL_LABELS: dict[str, str] = {
    Channel.NAVER_SEARCH: "네이버 검색",
    Channel.NAVER_GFA: "네이버 GFA",
    Channel.KAKAO_SEARCH: "카카오 검색",
    Channel.KAKAO_MOMENT: "카카오 모먼트",
    Channel.GOOGLE_SEARCH: "구글 검색",
    Channel.GOOGLE_GDN: "구글 GDN",
    Channel.META: "메타",
}

# 채널이 속한 플랫폼(광고관리자) 그룹
CHANNEL_PLATFORMS: dict[str, str] = {
    Channel.NAVER_SEARCH: "네이버",
    Channel.NAVER_GFA: "네이버",
    Channel.KAKAO_SEARCH: "카카오",
    Channel.KAKAO_MOMENT: "카카오",
    Channel.GOOGLE_SEARCH: "구글",
    Channel.GOOGLE_GDN: "구글",
    Channel.META: "메타",
}


@dataclass
class DailyMetric:
    """채널 x 캠페인 x 일자 단위의 통합 성과 지표."""

    date: date
    channel: str                # Channel 값
    campaign_id: str
    campaign_name: str
    impressions: int = 0
    clicks: int = 0
    cost: float = 0.0           # KRW
    conversions: float = 0.0
    revenue: float = 0.0        # 전환매출 KRW

    @property
    def ctr(self) -> float:
        return self.clicks / self.impressions * 100 if self.impressions else 0.0

    @property
    def cpc(self) -> float:
        return self.cost / self.clicks if self.clicks else 0.0

    @property
    def cpa(self) -> float:
        return self.cost / self.conversions if self.conversions else 0.0

    @property
    def roas(self) -> float:
        return self.revenue / self.cost * 100 if self.cost else 0.0

    def to_row(self) -> dict:
        d = asdict(self)
        d["date"] = self.date.isoformat()
        return d


@dataclass
class Ga4Daily:
    """GA4 일자 x 소스/매체 단위 지표."""

    date: date
    source_medium: str          # 예: "naver / cpc"
    sessions: int = 0
    engaged_sessions: int = 0
    conversions: float = 0.0
    revenue: float = 0.0
    avg_engagement_seconds: float = 0.0

    def to_row(self) -> dict:
        d = asdict(self)
        d["date"] = self.date.isoformat()
        return d


@dataclass
class ClarityDaily:
    """Microsoft Clarity 일자 단위 UX 지표."""

    date: date
    sessions: int = 0
    bot_sessions: int = 0
    dead_clicks: int = 0        # 반응 없는 클릭
    rage_clicks: int = 0        # 연타 클릭(불만 신호)
    quick_backs: int = 0        # 빠른 이탈
    excessive_scrolls: int = 0
    script_errors: int = 0
    avg_scroll_depth: float = 0.0   # %

    def to_row(self) -> dict:
        d = asdict(self)
        d["date"] = self.date.isoformat()
        return d


@dataclass
class CampaignSpec:
    """플랫폼 공통 캠페인 정의(자동 세팅 입력값).

    campaign_template.yaml 이 이 구조로 로드되고, 각 커넥터가
    자기 플랫폼의 API 페이로드로 변환한다.
    """

    name: str
    daily_budget: int                       # KRW
    start_date: str                         # YYYY-MM-DD
    end_date: str | None = None
    channels: list[str] = field(default_factory=list)   # Channel 값 목록
    landing_url: str = ""
    keywords: list[str] = field(default_factory=list)   # 검색 채널용
    headline: str = ""                       # 소재 제목
    description: str = ""                    # 소재 설명
    image_url: str = ""                      # 디스플레이 채널용
    age_min: int | None = None               # 타겟팅(디스플레이)
    age_max: int | None = None
    genders: list[str] = field(default_factory=list)     # ["male","female"]
    locations: list[str] = field(default_factory=list)   # ["KR"] 등


@dataclass
class LaunchResult:
    """캠페인 자동 세팅 결과(채널 1개당 1건)."""

    channel: str
    ok: bool
    campaign_id: str = ""
    message: str = ""
