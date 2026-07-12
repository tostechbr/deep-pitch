"""Testes do live_feed (football-data.org) — degradação + parsing (mock)."""

import httpx

from deep_pitch.tools import feed as lf
from deep_pitch.tools.feed import live_feed_for

_MATCHES = [
    {
        "utcDate": "2026-07-05T18:00:00Z",
        "status": "FINISHED",
        "stage": "QUARTER_FINALS",
        "homeTeam": {"name": "Norway"},
        "awayTeam": {"name": "Brazil"},
        "score": {"fullTime": {"home": 2, "away": 1}},
    },
    {
        "utcDate": "2026-07-11T18:00:00Z",
        "status": "SCHEDULED",
        "stage": "SEMI_FINALS",
        "homeTeam": {"name": "Norway"},
        "awayTeam": {"name": "England"},
        "score": {"fullTime": {"home": None, "away": None}},
    },
]


def test_degrades_without_token(make_settings):
    out = live_feed_for("Norway", make_settings(football_data_api_key=None))
    assert "indisponível" in out
    assert "FOOTBALL_DATA_API_KEY" in out


def test_parses_results_and_next(make_settings, monkeypatch):
    monkeypatch.setattr(lf, "_fetch_matches", lambda s: _MATCHES)
    out = live_feed_for("Norway", make_settings(football_data_api_key="tok"))
    assert "Norway 2-1 Brazil" in out          # resultado passado
    assert "Norway vs England (agendado)" in out  # próximo jogo
    assert "Semi Finals" in out


def test_team_not_found(make_settings, monkeypatch):
    monkeypatch.setattr(lf, "_fetch_matches", lambda s: _MATCHES)
    out = live_feed_for("Japan", make_settings(football_data_api_key="tok"))
    assert "não encontrado" in out


def test_rate_limit_message(make_settings, monkeypatch):
    def _429(s):
        resp = httpx.Response(429, request=httpx.Request("GET", "http://x"))
        raise httpx.HTTPStatusError("rate", request=resp.request, response=resp)

    monkeypatch.setattr(lf, "_fetch_matches", _429)
    out = live_feed_for("Norway", make_settings(football_data_api_key="tok"))
    assert "rate limit" in out


def test_network_error_message(make_settings, monkeypatch):
    def _boom(s):
        raise httpx.ConnectError("down")

    monkeypatch.setattr(lf, "_fetch_matches", _boom)
    out = live_feed_for("Norway", make_settings(football_data_api_key="tok"))
    assert "indisponível" in out


def test_non_json_200_degrades(make_settings, monkeypatch):
    # HTTP 200 com corpo não-JSON → resp.json() levanta ValueError; deve degradar, não quebrar
    def _bad(s):
        raise ValueError("Expecting value: line 1 column 1")

    monkeypatch.setattr(lf, "_fetch_matches", _bad)
    out = live_feed_for("Norway", make_settings(football_data_api_key="tok"))
    assert "indisponível" in out
