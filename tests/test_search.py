"""Testes do web_search (backend mockado — sem rede)."""

from deep_pitch.tools import search as se
from deep_pitch.tools.search import web_search

_FAKE = [
    {"title": "England injuries", "url": "https://ex.com/1", "snippet": "Rice a doubt vs Norway."},
    {"title": "Squad news", "url": "https://ex.com/2", "snippet": "Two players ill."},
]


def test_web_search_formats_results(monkeypatch):
    monkeypatch.setattr(se, "_search", lambda *a, **k: _FAKE)
    out = web_search.invoke({"query": "England injuries", "max_results": 2})
    assert "[1] England injuries" in out
    assert "https://ex.com/1" in out
    assert "Rice a doubt" in out


def test_web_search_empty(monkeypatch):
    monkeypatch.setattr(se, "_search", lambda *a, **k: [])
    out = web_search.invoke({"query": "nada aqui"})
    assert "Sem resultados" in out


def test_web_search_degrades_on_error(monkeypatch):
    def _boom(*a, **k):
        raise RuntimeError("rate limit")

    monkeypatch.setattr(se, "_search", _boom)
    out = web_search.invoke({"query": "x"})
    assert "indisponível" in out


def test_search_prefers_tavily_then_falls_back(monkeypatch, make_settings):
    calls = []
    monkeypatch.setattr(se, "_tavily_search", lambda *a, **k: (_ for _ in ()).throw(RuntimeError()))
    monkeypatch.setattr(se, "_ddg_search", lambda q, n: calls.append("ddg") or _FAKE)
    out = se._search("q", 3, make_settings(tavily_api_key="tvly"))
    assert calls == ["ddg"]  # Tavily falhou → caiu pro DDG
    assert out == _FAKE
