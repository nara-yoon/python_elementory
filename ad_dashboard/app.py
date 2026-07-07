"""통합 광고 대시보드 (Streamlit).

네이버 검색/GFA, 카카오 검색/모먼트, 구글 검색/GDN, 메타의 성과를
GA4 · Microsoft Clarity 와 함께 한 화면에서 본다.

실행:
    streamlit run app.py
"""
from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core import bulk_ops, campaign_launcher, collector, storage
from core.models import CHANNEL_LABELS, CHANNEL_PLATFORMS, CampaignSpec, Channel

# ---------------------------------------------------------------- 팔레트
# 검증된 카테고리 팔레트(라이트 모드) — 채널마다 고정 슬롯, 순서 변경 금지
CHANNEL_COLORS: dict[str, str] = {
    Channel.NAVER_SEARCH.value: "#2a78d6",   # slot 1 blue
    Channel.NAVER_GFA.value: "#1baf7a",      # slot 2 aqua
    Channel.KAKAO_SEARCH.value: "#eda100",   # slot 3 yellow
    Channel.KAKAO_MOMENT.value: "#008300",   # slot 4 green
    Channel.GOOGLE_SEARCH.value: "#4a3aa7",  # slot 5 violet
    Channel.GOOGLE_GDN.value: "#e34948",     # slot 6 red
    Channel.META.value: "#e87ba4",           # slot 7 magenta
}
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
BASELINE = "#c3c2b7"
# 순차(서수) 램프 — 퍼널 단계용, 파랑 한 색상 계열
ORDINAL_BLUES = ["#86b6ef", "#5598e7", "#2a78d6", "#1c5cab"]
FONT = 'system-ui, -apple-system, "Segoe UI", sans-serif'

CHANNEL_ORDER = list(CHANNEL_COLORS)  # 고정 순서

st.set_page_config(page_title="통합 광고 대시보드", page_icon="📊", layout="wide")


# ---------------------------------------------------------------- 데이터
@st.cache_data(ttl=300)
def load_all() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame,
                        pd.DataFrame, pd.DataFrame]:
    conn = storage.connect()
    metrics = storage.load_metrics(conn)
    hourly = storage.load_hourly(conn)
    ga4 = storage.load_ga4(conn)
    clarity = storage.load_clarity(conn)
    campaigns = storage.load_campaigns(conn)
    conn.close()
    return metrics, hourly, ga4, clarity, campaigns


def ensure_data() -> None:
    """DB가 비어 있으면 데모 데이터를 만들어 대시보드를 바로 체험하게 한다."""
    metrics, hourly, *_ = load_all()
    if metrics.empty:
        with st.spinner("처음 실행이라 데모 데이터를 생성하는 중입니다…"):
            collector.collect(demo=True)
        load_all.clear()
    elif hourly.empty and metrics["campaign_id"].str.startswith("demo_").all():
        # 구버전 데모 DB에는 시간대 데이터가 없으므로 한 번 백필한다
        from core import demo_data
        from core.models import DailyMetric
        rows = [DailyMetric(date=r.date.date(), channel=r.channel,
                            campaign_id=r.campaign_id, campaign_name=r.campaign_name,
                            impressions=r.impressions, clicks=r.clicks, cost=r.cost,
                            conversions=r.conversions, revenue=r.revenue)
                for r in metrics.itertuples()]
        conn = storage.connect()
        storage.upsert_hourly(conn, demo_data.generate_hourly(rows))
        conn.close()
        load_all.clear()


def won(x: float) -> str:
    if abs(x) >= 100_000_000:
        return f"{x / 100_000_000:,.1f}억원"
    if abs(x) >= 10_000_000:
        return f"{x / 10_000:,.0f}만원"
    return f"{x:,.0f}원"


def base_layout(fig: go.Figure, height: int = 360, unified: bool = False) -> go.Figure:
    fig.update_layout(
        height=height,
        paper_bgcolor=SURFACE, plot_bgcolor=SURFACE,
        font=dict(family=FONT, color=INK, size=13),
        margin=dict(l=8, r=8, t=8, b=8),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0,
                    font=dict(color=INK_2)),
        hovermode="x unified" if unified else "closest",
        hoverlabel=dict(bgcolor="white", font=dict(family=FONT, color=INK)),
    )
    fig.update_xaxes(gridcolor=GRID, linecolor=BASELINE, zeroline=False,
                     tickfont=dict(color=MUTED))
    fig.update_yaxes(gridcolor=GRID, linecolor=BASELINE, zeroline=False,
                     tickfont=dict(color=MUTED))
    return fig


ensure_data()
metrics_df, hourly_df, ga4_df, clarity_df, campaigns_df = load_all()
metrics_df["채널"] = metrics_df["channel"].map(CHANNEL_LABELS)
metrics_df["플랫폼"] = metrics_df["channel"].map(CHANNEL_PLATFORMS)

# ---------------------------------------------------------------- 헤더 + 필터
st.title("📊 통합 광고 대시보드")
st.caption("네이버 검색·GFA / 카카오 검색·모먼트 / 구글 검색·GDN / 메타 + GA4 · Microsoft Clarity")

fcol1, fcol2 = st.columns([1, 3])
with fcol1:
    period = st.radio("기간", ["최근 7일", "최근 30일", "최근 90일"],
                      index=1, horizontal=True)
with fcol2:
    selected_channels = st.multiselect(
        "채널", options=CHANNEL_ORDER,
        default=CHANNEL_ORDER,
        format_func=lambda c: CHANNEL_LABELS[c],
    )

days = {"최근 7일": 7, "최근 30일": 30, "최근 90일": 90}[period]
max_date = metrics_df["date"].max() if not metrics_df.empty else pd.Timestamp(date.today())
start_ts = max_date - pd.Timedelta(days=days - 1)
prev_start_ts = start_ts - pd.Timedelta(days=days)

cur = metrics_df[(metrics_df["date"] >= start_ts)
                 & (metrics_df["channel"].isin(selected_channels))]
prev = metrics_df[(metrics_df["date"] >= prev_start_ts) & (metrics_df["date"] < start_ts)
                  & (metrics_df["channel"].isin(selected_channels))]

tab_overview, tab_hourly, tab_detail, tab_ga4, tab_clarity, tab_launch = st.tabs(
    ["통합 개요", "시간대 분석", "채널·캠페인 상세", "GA4 분석", "Clarity UX",
     "캠페인 자동 세팅"])

# ================================================================ 통합 개요
with tab_overview:
    if cur.empty:
        st.info("선택한 조건에 데이터가 없습니다. 채널/기간을 바꾸거나 데이터를 수집하세요.")
    else:
        def _sums(df: pd.DataFrame) -> dict:
            s = df[["impressions", "clicks", "cost", "conversions", "revenue"]].sum()
            return {
                "cost": s.cost, "impressions": s.impressions, "clicks": s.clicks,
                "ctr": s.clicks / s.impressions * 100 if s.impressions else 0,
                "conversions": s.conversions,
                "roas": s.revenue / s.cost * 100 if s.cost else 0,
            }

        now_kpi, prev_kpi = _sums(cur), _sums(prev)

        def _delta(key: str, pct: bool = False) -> str:
            base = prev_kpi[key]
            if not base:
                return ""
            diff = now_kpi[key] - base
            if pct:
                return f"{diff:+.1f}%p"
            return f"{diff / base * 100:+.1f}%"

        k1, k2, k3, k4, k5, k6 = st.columns(6)
        k1.metric("총 광고비", won(now_kpi["cost"]), _delta("cost"),
                  delta_color="inverse")
        k2.metric("노출", f"{now_kpi['impressions']:,.0f}", _delta("impressions"))
        k3.metric("클릭", f"{now_kpi['clicks']:,.0f}", _delta("clicks"))
        k4.metric("CTR", f"{now_kpi['ctr']:.2f}%", _delta("ctr", pct=True))
        k5.metric("전환", f"{now_kpi['conversions']:,.0f}", _delta("conversions"))
        k6.metric("ROAS", f"{now_kpi['roas']:,.0f}%", _delta("roas", pct=True))
        st.caption(f"증감은 직전 {days}일 대비입니다. 광고비는 감소가 좋음(녹색)으로 표시됩니다.")

        st.divider()

        # ---- 일별 추이 (채널별 라인)
        c_trend, c_metric = st.columns([5, 1])
        with c_metric:
            metric_key = st.selectbox(
                "지표", ["cost", "clicks", "conversions", "revenue"],
                format_func={"cost": "광고비", "clicks": "클릭",
                             "conversions": "전환", "revenue": "매출"}.get)
        with c_trend:
            st.subheader("일별 추이")
        daily = (cur.groupby(["date", "channel"], as_index=False)[metric_key].sum())
        fig = go.Figure()
        for ch in CHANNEL_ORDER:
            part = daily[daily["channel"] == ch]
            if part.empty:
                continue
            fig.add_trace(go.Scatter(
                x=part["date"], y=part[metric_key],
                name=CHANNEL_LABELS[ch], mode="lines",
                line=dict(color=CHANNEL_COLORS[ch], width=2),
            ))
        base_layout(fig, height=380, unified=True)
        st.plotly_chart(fig, use_container_width=True)

        # ---- 채널 비교 (광고비 / ROAS)
        by_ch = cur.groupby("channel", as_index=False).agg(
            cost=("cost", "sum"), revenue=("revenue", "sum"),
            clicks=("clicks", "sum"), impressions=("impressions", "sum"),
            conversions=("conversions", "sum"))
        by_ch["roas"] = (by_ch["revenue"] / by_ch["cost"] * 100).fillna(0)
        by_ch = by_ch.set_index("channel").reindex(
            [c for c in CHANNEL_ORDER if c in by_ch["channel"].values
             or c in by_ch.index]).dropna(how="all").reset_index()

        b1, b2 = st.columns(2)
        with b1:
            st.subheader("채널별 광고비")
            d = by_ch.sort_values("cost")
            fig = go.Figure(go.Bar(
                x=d["cost"], y=d["channel"].map(CHANNEL_LABELS), orientation="h",
                marker=dict(color=[CHANNEL_COLORS[c] for c in d["channel"]],
                            cornerradius=4),
                text=[won(v) for v in d["cost"]], textposition="outside",
                textfont=dict(color=INK_2, size=12), width=0.55,
                cliponaxis=False,
                hovertemplate="%{y}: %{text}<extra></extra>",
            ))
            base_layout(fig, height=340)
            fig.update_xaxes(showticklabels=False, showgrid=False,
                             range=[0, d["cost"].max() * 1.25])
            st.plotly_chart(fig, use_container_width=True)
        with b2:
            st.subheader("채널별 ROAS")
            d = by_ch.sort_values("roas")
            fig = go.Figure(go.Bar(
                x=d["roas"], y=d["channel"].map(CHANNEL_LABELS), orientation="h",
                marker=dict(color=[CHANNEL_COLORS[c] for c in d["channel"]],
                            cornerradius=4),
                text=[f"{v:,.0f}%" for v in d["roas"]], textposition="outside",
                textfont=dict(color=INK_2, size=12), width=0.55,
                cliponaxis=False,
                hovertemplate="%{y}: ROAS %{x:,.0f}%<extra></extra>",
            ))
            fig.add_vline(x=100, line_color=BASELINE, line_dash="dash")
            base_layout(fig, height=340)
            fig.update_xaxes(showgrid=False, ticksuffix="%",
                             range=[0, d["roas"].max() * 1.2])
            st.plotly_chart(fig, use_container_width=True)
            st.caption("점선은 손익분기(ROAS 100%)입니다.")

        # ---- 퍼널: 노출 → 클릭 → 세션(GA4) → 전환
        st.subheader("전환 퍼널")
        ga4_cur = ga4_df[(ga4_df["date"] >= start_ts)
                         & (ga4_df["source_medium"] != "google / organic")]
        sessions_total = ga4_cur["sessions"].sum()
        stages = [("노출", now_kpi["impressions"]), ("클릭", now_kpi["clicks"]),
                  ("세션 (GA4)", sessions_total), ("전환", now_kpi["conversions"])]
        f1, f2, f3, f4 = st.columns(4)
        for col, (label, value) in zip((f1, f2, f3, f4), stages):
            col.metric(label, f"{value:,.0f}")

        # 규모 차이가 커서(노출≫전환) 절대값 퍼널 대신 단계 간 전환율로 본다
        rates = [
            ("세션 → 전환 (CVR)",
             now_kpi["conversions"] / sessions_total * 100 if sessions_total else 0),
            ("클릭 → 세션 (유입률)",
             sessions_total / now_kpi["clicks"] * 100 if now_kpi["clicks"] else 0),
            ("노출 → 클릭 (CTR)", now_kpi["ctr"]),
        ]
        fig = go.Figure(go.Bar(
            x=[r[1] for r in rates], y=[r[0] for r in rates], orientation="h",
            marker=dict(color=["#0d366b", "#2a78d6", "#86b6ef"], cornerradius=4),
            text=[f"{r[1]:.2f}%" for r in rates], textposition="outside",
            textfont=dict(color=INK_2, size=12), width=0.5,
            hovertemplate="%{y}: %{x:.2f}%<extra></extra>",
        ))
        base_layout(fig, height=260)
        fig.update_xaxes(ticksuffix="%", showgrid=False)
        st.plotly_chart(fig, use_container_width=True)
        st.caption("세션은 GA4 유료 채널 세션 합계입니다. 노출→클릭→방문→전환에서 "
                   "전환율이 가장 낮은 구간부터 개선하세요.")

        with st.expander("📋 원본 데이터 테이블 보기"):
            table = by_ch.copy()
            table["채널"] = table["channel"].map(CHANNEL_LABELS)
            table["CTR%"] = (table["clicks"] / table["impressions"] * 100).round(2)
            table["CPC"] = (table["cost"] / table["clicks"]).round(0)
            table["CPA"] = (table["cost"] / table["conversions"]).round(0)
            st.dataframe(
                table[["채널", "impressions", "clicks", "CTR%", "CPC",
                       "cost", "conversions", "CPA", "revenue", "roas"]]
                .rename(columns={"impressions": "노출", "clicks": "클릭",
                                 "cost": "광고비", "conversions": "전환",
                                 "revenue": "매출", "roas": "ROAS%"}),
                use_container_width=True, hide_index=True)

# ================================================================ 시간대 분석
with tab_hourly:
    hcur = hourly_df[(hourly_df["date"] >= start_ts)
                     & (hourly_df["channel"].isin(selected_channels))]
    if hcur.empty:
        st.info("시간대 데이터가 없습니다. `python cli.py collect` (데모는 --demo) 를 "
                "실행하세요. 카카오/구글/메타는 시간대 API를 지원하며, 네이버는 "
                "시간대 분해를 API로 제공하지 않아 실데이터에서는 제외됩니다.")
    else:
        h_head, h_sel = st.columns([5, 1])
        with h_sel:
            h_metric = st.selectbox(
                "지표", ["cost", "impressions", "clicks", "conversions"],
                format_func={"cost": "광고비", "impressions": "노출",
                             "clicks": "클릭", "conversions": "전환"}.get,
                key="hourly_metric")
        with h_head:
            st.subheader("시간대 히트맵")

        # ---- 피크 시간대 요약
        by_hour = hcur.groupby("hour")[["cost", "conversions", "clicks"]].sum()
        eff = (by_hour["conversions"] / by_hour["cost"].replace(0, pd.NA) * 10_000)
        p1, p2, p3 = st.columns(3)
        p1.metric("광고비 피크", f"{by_hour['cost'].idxmax()}시")
        p2.metric("전환 피크", f"{by_hour['conversions'].idxmax()}시")
        p3.metric("전환 효율 최고 (전환/만원)", f"{eff.idxmax()}시")

        WEEKDAYS = ["월", "화", "수", "목", "금", "토", "일"]
        # 순차 램프(파랑, 밝음→어두움) — 히트맵은 단일 색상 계열만 사용
        BLUE_SCALE = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5",
                      "#256abf", "#184f95", "#0d366b"]
        hover_unit = {"cost": "원", "impressions": "", "clicks": "", "conversions": ""}

        def heatmap(z, y_labels, title, hovertemplate) -> None:
            st.markdown(f"**{title}**")
            fig = go.Figure(go.Heatmap(
                z=z, x=[f"{h}시" for h in range(24)], y=y_labels,
                colorscale=BLUE_SCALE, xgap=2, ygap=2,
                hovertemplate=hovertemplate + "<extra></extra>",
                colorbar=dict(tickfont=dict(color=MUTED), thickness=12,
                              outlinewidth=0),
            ))
            base_layout(fig, height=60 + 34 * len(y_labels))
            fig.update_xaxes(showgrid=False, dtick=1)
            fig.update_yaxes(showgrid=False, autorange="reversed")
            st.plotly_chart(fig, use_container_width=True)

        # ---- 요일 x 시간 (하루 평균값)
        tmp = hcur.groupby(["date", "hour"], as_index=False)[h_metric].sum()
        tmp["weekday"] = tmp["date"].dt.weekday
        pivot_wd = (tmp.groupby(["weekday", "hour"])[h_metric].mean()
                    .unstack(fill_value=0).reindex(range(7), fill_value=0)
                    .reindex(columns=range(24), fill_value=0))
        heatmap(pivot_wd.values, WEEKDAYS,
                "요일 × 시간대 (일평균)",
                "%{y}요일 %{x}: %{z:,.0f}" + hover_unit[h_metric])

        # ---- 채널 x 시간 (채널 내 비중 %) — 채널마다 규모가 달라 비중으로 비교
        by_ch_hour = (hcur.groupby(["channel", "hour"])[h_metric].sum()
                      .unstack(fill_value=0).reindex(columns=range(24), fill_value=0))
        by_ch_hour = by_ch_hour.reindex(
            [c for c in CHANNEL_ORDER if c in by_ch_hour.index])
        share = by_ch_hour.div(by_ch_hour.sum(axis=1).replace(0, pd.NA), axis=0) * 100
        heatmap(share.round(1).values,
                [CHANNEL_LABELS[c] for c in share.index],
                "채널 × 시간대 (각 채널 내 비중 %)",
                "%{y} %{x}: %{z:.1f}%")
        st.caption("채널 × 시간대는 채널별 규모 차이를 없애기 위해 각 채널 합계 대비 "
                   "비중(%)으로 표시합니다. 진할수록 그 채널의 성과가 몰리는 시간대입니다.")

        with st.expander("📋 시간대 원본 데이터 테이블 보기"):
            table = (hcur.groupby("hour", as_index=False)
                     [["impressions", "clicks", "cost", "conversions", "revenue"]]
                     .sum())
            table["시간대"] = table["hour"].map(lambda h: f"{h:02d}:00~{h:02d}:59")
            st.dataframe(
                table[["시간대", "impressions", "clicks", "cost",
                       "conversions", "revenue"]]
                .rename(columns={"impressions": "노출", "clicks": "클릭",
                                 "cost": "광고비", "conversions": "전환",
                                 "revenue": "매출"}),
                use_container_width=True, hide_index=True)

# ================================================================ 채널·캠페인 상세
with tab_detail:
    ch = st.selectbox("채널 선택", CHANNEL_ORDER,
                      format_func=lambda c: CHANNEL_LABELS[c])
    ch_df = cur[cur["channel"] == ch]
    if ch_df.empty:
        st.info("이 채널의 데이터가 없습니다.")
    else:
        by_camp = ch_df.groupby(["campaign_id", "campaign_name"], as_index=False).agg(
            impressions=("impressions", "sum"), clicks=("clicks", "sum"),
            cost=("cost", "sum"), conversions=("conversions", "sum"),
            revenue=("revenue", "sum"))
        by_camp["CTR%"] = (by_camp["clicks"] / by_camp["impressions"] * 100).round(2)
        by_camp["CPC"] = (by_camp["cost"] / by_camp["clicks"]).round(0)
        by_camp["CPA"] = (by_camp["cost"] / by_camp["conversions"]).round(0)
        by_camp["ROAS%"] = (by_camp["revenue"] / by_camp["cost"] * 100).round(0)

        st.subheader(f"{CHANNEL_LABELS[ch]} · 캠페인 성과")
        st.dataframe(
            by_camp.rename(columns={
                "campaign_id": "캠페인 ID", "campaign_name": "캠페인",
                "impressions": "노출", "clicks": "클릭", "cost": "광고비",
                "conversions": "전환", "revenue": "매출"}),
            use_container_width=True, hide_index=True)

        st.subheader("캠페인별 일별 광고비")
        daily_camp = ch_df.groupby(["date", "campaign_name"], as_index=False)["cost"].sum()
        # 이 채널 색을 앵커로, 캠페인은 같은 색의 명도 단계로 구분(채널 정체성 유지)
        shades = [CHANNEL_COLORS[ch], "#898781", "#c3c2b7"]
        fig = go.Figure()
        for i, camp in enumerate(sorted(daily_camp["campaign_name"].unique())):
            part = daily_camp[daily_camp["campaign_name"] == camp]
            fig.add_trace(go.Scatter(
                x=part["date"], y=part["cost"], name=camp, mode="lines",
                line=dict(color=shades[i % len(shades)], width=2)))
        base_layout(fig, height=340, unified=True)
        st.plotly_chart(fig, use_container_width=True)

# ================================================================ GA4 분석
with tab_ga4:
    ga4_cur = ga4_df[ga4_df["date"] >= start_ts]
    if ga4_cur.empty:
        st.info("GA4 데이터가 없습니다. `.env` 에 GA4 자격증명을 넣고 `python cli.py collect` 를 실행하세요.")
    else:
        s = ga4_cur[["sessions", "engaged_sessions", "conversions", "revenue"]].sum()
        g1, g2, g3, g4 = st.columns(4)
        g1.metric("세션", f"{s.sessions:,.0f}")
        g2.metric("참여 세션율", f"{s.engaged_sessions / s.sessions * 100:.1f}%"
                  if s.sessions else "-")
        g3.metric("전환 (GA4)", f"{s.conversions:,.0f}")
        g4.metric("매출 (GA4)", won(s.revenue))

        st.subheader("소스/매체별 일별 세션")
        top_sources = (ga4_cur.groupby("source_medium")["sessions"].sum()
                       .sort_values(ascending=False).head(7).index.tolist())
        # 색은 순위가 아니라 소스(엔티티)를 따라 고정 — 기간을 바꿔도 색이 유지된다
        palette = list(CHANNEL_COLORS.values()) + ["#eb6834"]  # slot 8 orange
        all_sources = sorted(ga4_df["source_medium"].unique())
        source_color = {sm: palette[i % len(palette)]
                        for i, sm in enumerate(all_sources)}
        fig = go.Figure()
        for sm in sorted(top_sources):
            part = (ga4_cur[ga4_cur["source_medium"] == sm]
                    .groupby("date", as_index=False)["sessions"].sum())
            fig.add_trace(go.Scatter(
                x=part["date"], y=part["sessions"], name=sm, mode="lines",
                line=dict(color=source_color[sm], width=2)))
        base_layout(fig, height=380, unified=True)
        st.plotly_chart(fig, use_container_width=True)
        st.caption("세션 상위 7개 소스/매체만 표시합니다.")

        st.subheader("소스/매체별 성과")
        by_sm = ga4_cur.groupby("source_medium", as_index=False).agg(
            sessions=("sessions", "sum"), engaged=("engaged_sessions", "sum"),
            conversions=("conversions", "sum"), revenue=("revenue", "sum"))
        by_sm["참여율%"] = (by_sm["engaged"] / by_sm["sessions"] * 100).round(1)
        by_sm["세션당 전환율%"] = (by_sm["conversions"] / by_sm["sessions"] * 100).round(2)
        st.dataframe(
            by_sm.sort_values("sessions", ascending=False)
            .rename(columns={"source_medium": "소스/매체", "sessions": "세션",
                             "engaged": "참여 세션", "conversions": "전환",
                             "revenue": "매출"}),
            use_container_width=True, hide_index=True)

# ================================================================ Clarity UX
with tab_clarity:
    cl = clarity_df[clarity_df["date"] >= start_ts]
    if cl.empty:
        st.info("Clarity 데이터가 없습니다. `.env` 에 CLARITY_API_TOKEN 을 넣고 매일 "
                "`python cli.py collect` 를 실행해 쌓아주세요 (API가 최근 1~3일만 제공).")
    else:
        total_sessions = cl["sessions"].sum()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("세션 (Clarity)", f"{total_sessions:,.0f}")
        c2.metric("평균 스크롤 깊이", f"{cl['avg_scroll_depth'].mean():.1f}%")
        c3.metric("데드 클릭률", f"{cl['dead_clicks'].sum() / total_sessions * 100:.1f}%"
                  if total_sessions else "-")
        c4.metric("레이지 클릭률", f"{cl['rage_clicks'].sum() / total_sessions * 100:.1f}%"
                  if total_sessions else "-")

        st.subheader("UX 이슈 발생률 추이")
        issue = cl.copy()
        for col in ["dead_clicks", "rage_clicks", "quick_backs", "script_errors"]:
            issue[col + "_rate"] = issue[col] / issue["sessions"] * 100
        series = [("dead_clicks_rate", "데드 클릭", "#2a78d6"),
                  ("rage_clicks_rate", "레이지 클릭", "#1baf7a"),
                  ("quick_backs_rate", "퀵백(즉시 이탈)", "#eda100"),
                  ("script_errors_rate", "스크립트 오류", "#008300")]
        fig = go.Figure()
        for col, name, color in series:
            fig.add_trace(go.Scatter(
                x=issue["date"], y=issue[col], name=name, mode="lines",
                line=dict(color=color, width=2)))
        base_layout(fig, height=360, unified=True)
        fig.update_yaxes(ticksuffix="%")
        st.plotly_chart(fig, use_container_width=True)
        st.caption("데드 클릭: 반응 없는 요소 클릭 · 레이지 클릭: 같은 곳 연타(불만 신호) · "
                   "퀵백: 진입 직후 되돌아감. 급증하면 랜딩페이지 점검이 필요합니다.")

        st.subheader("스크롤 깊이 추이")
        fig = go.Figure(go.Scatter(
            x=cl["date"], y=cl["avg_scroll_depth"], mode="lines",
            line=dict(color="#2a78d6", width=2),
            hovertemplate="%{x|%m/%d}: %{y:.1f}%<extra></extra>"))
        base_layout(fig, height=280)
        fig.update_yaxes(ticksuffix="%", range=[0, 100])
        st.plotly_chart(fig, use_container_width=True)

        with st.expander("📋 Clarity 원본 데이터"):
            st.dataframe(cl.sort_values("date", ascending=False),
                         use_container_width=True, hide_index=True)

# ================================================================ 캠페인 자동 세팅
with tab_launch:
    st.subheader("새 캠페인 자동 세팅")
    st.caption("아래 한 번의 입력으로 선택한 모든 채널에 캠페인이 생성됩니다. "
               "자격증명이 없는 채널은 시뮬레이션으로 처리됩니다.")

    with st.form("launch_form"):
        name = st.text_input("캠페인 이름", "2026 여름 신제품 런칭")
        col1, col2, col3 = st.columns(3)
        with col1:
            daily_budget = st.number_input("일 예산 (원)", min_value=10_000,
                                           value=100_000, step=10_000)
        with col2:
            start_d = st.date_input("시작일", date.today() + timedelta(days=1))
        with col3:
            end_d = st.date_input("종료일", date.today() + timedelta(days=30))
        channels = st.multiselect(
            "채널", CHANNEL_ORDER, default=CHANNEL_ORDER,
            format_func=lambda c: CHANNEL_LABELS[c])
        landing_url = st.text_input("랜딩 URL", "https://example.com")
        keywords_raw = st.text_area("키워드 (검색 채널용, 줄바꿈으로 구분)",
                                    "여름 신상\n신제품 추천")
        col4, col5 = st.columns(2)
        with col4:
            headline = st.text_input("소재 제목", "여름 신제품 런칭")
        with col5:
            image_url = st.text_input("이미지 URL (디스플레이 채널용)", "")
        description = st.text_input("소재 설명", "지금 구매하면 최대 30% 할인")
        col6, col7 = st.columns(2)
        with col6:
            age_range = st.slider("타겟 연령", 15, 65, (25, 44))
        with col7:
            genders = st.multiselect("타겟 성별", ["male", "female"],
                                     format_func={"male": "남성", "female": "여성"}.get)
        submitted = st.form_submit_button("🚀 캠페인 세팅 실행", type="primary")

    if submitted:
        spec = CampaignSpec(
            name=name, daily_budget=int(daily_budget),
            start_date=start_d.isoformat(), end_date=end_d.isoformat(),
            channels=channels, landing_url=landing_url,
            keywords=[k.strip() for k in keywords_raw.splitlines() if k.strip()],
            headline=headline, description=description, image_url=image_url,
            age_min=age_range[0], age_max=age_range[1],
            genders=genders, locations=["KR"],
        )
        results = campaign_launcher.launch(spec)
        ok_count = sum(1 for r in results if r.ok)
        st.success(f"{len(results)}개 채널 중 {ok_count}개 세팅 완료")
        for r in results:
            label = CHANNEL_LABELS.get(r.channel, r.channel)
            if r.ok:
                st.write(f"✅ **{label}** · ID `{r.campaign_id}` — {r.message}")
            else:
                st.write(f"❌ **{label}** — {r.message}")
        load_all.clear()

    st.divider()
    st.subheader("대량 작업 (CSV)")
    st.caption("CSV 한 장으로 여러 캠페인을 한 번에 등록하거나, 여러 캠페인의 소재를 "
               "일괄 교체합니다. 엑셀에서 편집한 CSV(UTF-8) 그대로 올리면 됩니다.")

    def _show_bulk_results(rows) -> None:
        total = sum(len(r.results) for r in rows)
        ok = sum(1 for row in rows for r in row.results if r.ok)
        (st.success if ok == total else st.warning)(f"{total}건 중 {ok}건 성공")
        for row in rows:
            for r in row.results:
                label = CHANNEL_LABELS.get(r.channel, r.channel)
                icon = "✅" if r.ok else "❌"
                st.write(f"{icon} [행 {row.row}] **{label}** · "
                         f"`{r.campaign_id or '-'}` — {r.message}")

    config_dir = Path(__file__).resolve().parent / "config"

    with st.expander("📦 캠페인 대량 등록 — 행 1개 = 캠페인 1개, 채널은 | 로 구분"):
        st.download_button(
            "샘플 CSV 내려받기",
            data=(config_dir / "bulk_campaigns_sample.csv").read_bytes(),
            file_name="bulk_campaigns_sample.csv", mime="text/csv",
            key="dl_bulk_campaigns")
        up = st.file_uploader("캠페인 CSV 업로드", type="csv", key="up_bulk_campaigns")
        if up is not None:
            df_up = pd.read_csv(up, dtype=str).fillna("")
            missing = bulk_ops.validate_columns(df_up, bulk_ops.CAMPAIGN_REQUIRED)
            if missing:
                st.error(f"필수 컬럼이 없습니다: {', '.join(missing)}")
            else:
                st.dataframe(df_up, use_container_width=True, hide_index=True)
                n_jobs = sum(len(str(ch).split("|")) for ch in df_up["channels"])
                if st.button(f"🚀 캠페인 {len(df_up)}개 → 총 {n_jobs}건 등록 실행",
                             type="primary", key="btn_bulk_launch"):
                    _show_bulk_results(bulk_ops.bulk_launch(df_up))
                    load_all.clear()

    with st.expander("🎨 소재 대량 변경 — 행 1개 = (채널, 캠페인 ID) 1건"):
        st.download_button(
            "샘플 CSV 내려받기",
            data=(config_dir / "bulk_creatives_sample.csv").read_bytes(),
            file_name="bulk_creatives_sample.csv", mime="text/csv",
            key="dl_bulk_creatives")
        st.caption("캠페인 ID는 아래 '세팅된 캠페인' 표 또는 각 광고관리자에서 확인하세요. "
                   "대부분의 플랫폼은 소재 '수정' 대신 새 소재를 등록하는 방식이라, "
                   "기존 소재는 확인 후 각 관리자에서 중지하면 됩니다.")
        up2 = st.file_uploader("소재 CSV 업로드", type="csv", key="up_bulk_creatives")
        if up2 is not None:
            df_up2 = pd.read_csv(up2, dtype=str).fillna("")
            missing = bulk_ops.validate_columns(df_up2, bulk_ops.CREATIVE_REQUIRED)
            if missing:
                st.error(f"필수 컬럼이 없습니다: {', '.join(missing)}")
            else:
                st.dataframe(df_up2, use_container_width=True, hide_index=True)
                if st.button(f"🎨 소재 변경 {len(df_up2)}건 실행",
                             type="primary", key="btn_bulk_creative"):
                    _show_bulk_results(bulk_ops.bulk_update_creatives(df_up2))

        _conn = storage.connect()
        history = storage.load_creative_updates(_conn)
        _conn.close()
        if not history.empty:
            st.markdown("**소재 변경 이력**")
            history["채널"] = history["channel"].map(CHANNEL_LABELS)
            st.dataframe(
                history[["created_at", "채널", "campaign_id", "headline",
                         "status", "message"]]
                .rename(columns={"created_at": "시각", "campaign_id": "캠페인 ID",
                                 "headline": "소재 제목", "status": "결과",
                                 "message": "상세"}),
                use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("세팅된 캠페인")
    if campaigns_df.empty:
        st.info("아직 세팅된 캠페인이 없습니다.")
    else:
        view = campaigns_df.copy()
        view["채널"] = view["channel"].map(CHANNEL_LABELS)
        st.dataframe(
            view[["채널", "campaign_id", "campaign_name", "daily_budget",
                  "status", "created_at"]]
            .rename(columns={"campaign_id": "캠페인 ID", "campaign_name": "캠페인",
                             "daily_budget": "일 예산", "status": "상태",
                             "created_at": "생성 시각"}),
            use_container_width=True, hide_index=True)
