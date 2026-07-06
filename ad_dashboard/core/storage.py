"""SQLite 저장소.

수집한 성과 데이터를 로컬 SQLite DB에 적재하고, 대시보드가 pandas 로 읽는다.
(date, channel, campaign_id) 를 기본키로 upsert 하므로 재수집해도 중복되지 않는다.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from .models import ClarityDaily, DailyMetric, Ga4Daily

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "ad_dashboard.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS metrics_daily (
    date TEXT NOT NULL,
    channel TEXT NOT NULL,
    campaign_id TEXT NOT NULL,
    campaign_name TEXT NOT NULL,
    impressions INTEGER DEFAULT 0,
    clicks INTEGER DEFAULT 0,
    cost REAL DEFAULT 0,
    conversions REAL DEFAULT 0,
    revenue REAL DEFAULT 0,
    PRIMARY KEY (date, channel, campaign_id)
);
CREATE TABLE IF NOT EXISTS ga4_daily (
    date TEXT NOT NULL,
    source_medium TEXT NOT NULL,
    sessions INTEGER DEFAULT 0,
    engaged_sessions INTEGER DEFAULT 0,
    conversions REAL DEFAULT 0,
    revenue REAL DEFAULT 0,
    avg_engagement_seconds REAL DEFAULT 0,
    PRIMARY KEY (date, source_medium)
);
CREATE TABLE IF NOT EXISTS clarity_daily (
    date TEXT PRIMARY KEY,
    sessions INTEGER DEFAULT 0,
    bot_sessions INTEGER DEFAULT 0,
    dead_clicks INTEGER DEFAULT 0,
    rage_clicks INTEGER DEFAULT 0,
    quick_backs INTEGER DEFAULT 0,
    excessive_scrolls INTEGER DEFAULT 0,
    script_errors INTEGER DEFAULT 0,
    avg_scroll_depth REAL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS campaigns (
    channel TEXT NOT NULL,
    campaign_id TEXT NOT NULL,
    campaign_name TEXT NOT NULL,
    daily_budget INTEGER DEFAULT 0,
    status TEXT DEFAULT 'ENABLED',
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    PRIMARY KEY (channel, campaign_id)
);
"""


def connect(db_path: Path | str = DB_PATH) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.executescript(_SCHEMA)
    return conn


def upsert_metrics(conn: sqlite3.Connection, rows: list[DailyMetric]) -> int:
    sql = """INSERT INTO metrics_daily
             (date, channel, campaign_id, campaign_name,
              impressions, clicks, cost, conversions, revenue)
             VALUES (:date, :channel, :campaign_id, :campaign_name,
                     :impressions, :clicks, :cost, :conversions, :revenue)
             ON CONFLICT(date, channel, campaign_id) DO UPDATE SET
                 campaign_name=excluded.campaign_name,
                 impressions=excluded.impressions,
                 clicks=excluded.clicks,
                 cost=excluded.cost,
                 conversions=excluded.conversions,
                 revenue=excluded.revenue"""
    conn.executemany(sql, [r.to_row() for r in rows])
    conn.commit()
    return len(rows)


def upsert_ga4(conn: sqlite3.Connection, rows: list[Ga4Daily]) -> int:
    sql = """INSERT INTO ga4_daily
             (date, source_medium, sessions, engaged_sessions,
              conversions, revenue, avg_engagement_seconds)
             VALUES (:date, :source_medium, :sessions, :engaged_sessions,
                     :conversions, :revenue, :avg_engagement_seconds)
             ON CONFLICT(date, source_medium) DO UPDATE SET
                 sessions=excluded.sessions,
                 engaged_sessions=excluded.engaged_sessions,
                 conversions=excluded.conversions,
                 revenue=excluded.revenue,
                 avg_engagement_seconds=excluded.avg_engagement_seconds"""
    conn.executemany(sql, [r.to_row() for r in rows])
    conn.commit()
    return len(rows)


def upsert_clarity(conn: sqlite3.Connection, rows: list[ClarityDaily]) -> int:
    sql = """INSERT INTO clarity_daily
             (date, sessions, bot_sessions, dead_clicks, rage_clicks,
              quick_backs, excessive_scrolls, script_errors, avg_scroll_depth)
             VALUES (:date, :sessions, :bot_sessions, :dead_clicks, :rage_clicks,
                     :quick_backs, :excessive_scrolls, :script_errors, :avg_scroll_depth)
             ON CONFLICT(date) DO UPDATE SET
                 sessions=excluded.sessions,
                 bot_sessions=excluded.bot_sessions,
                 dead_clicks=excluded.dead_clicks,
                 rage_clicks=excluded.rage_clicks,
                 quick_backs=excluded.quick_backs,
                 excessive_scrolls=excluded.excessive_scrolls,
                 script_errors=excluded.script_errors,
                 avg_scroll_depth=excluded.avg_scroll_depth"""
    conn.executemany(sql, [r.to_row() for r in rows])
    conn.commit()
    return len(rows)


def save_campaign(conn: sqlite3.Connection, channel: str, campaign_id: str,
                  campaign_name: str, daily_budget: int, status: str = "ENABLED") -> None:
    conn.execute(
        """INSERT INTO campaigns (channel, campaign_id, campaign_name, daily_budget, status)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(channel, campaign_id) DO UPDATE SET
               campaign_name=excluded.campaign_name,
               daily_budget=excluded.daily_budget,
               status=excluded.status""",
        (channel, campaign_id, campaign_name, daily_budget, status),
    )
    conn.commit()


def load_metrics(conn: sqlite3.Connection) -> pd.DataFrame:
    df = pd.read_sql_query("SELECT * FROM metrics_daily", conn, parse_dates=["date"])
    return df


def load_ga4(conn: sqlite3.Connection) -> pd.DataFrame:
    return pd.read_sql_query("SELECT * FROM ga4_daily", conn, parse_dates=["date"])


def load_clarity(conn: sqlite3.Connection) -> pd.DataFrame:
    return pd.read_sql_query("SELECT * FROM clarity_daily", conn, parse_dates=["date"])


def load_campaigns(conn: sqlite3.Connection) -> pd.DataFrame:
    return pd.read_sql_query(
        "SELECT * FROM campaigns ORDER BY created_at DESC", conn
    )
