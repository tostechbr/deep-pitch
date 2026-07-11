"""Testes do loader (filtros, cache TTL, download atômico, validação)."""

import os
import time

import pandas as pd
import pytest

from deep_pitch.data import load_results, played_matches, wc2026_fixtures
from deep_pitch.data import loader

_HEADER = "date,home_team,away_team,home_score,away_score,tournament,city,country,neutral"


def _sample_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.to_datetime(["2018-06-01", "2026-07-10", "2026-07-11", "2026-07-11"]),
            "home_team": ["A", "Spain", "Norway", "Argentina"],
            "away_team": ["B", "Belgium", "England", "Switzerland"],
            "home_score": [1.0, 2.0, None, None],
            "away_score": [0.0, 1.0, None, None],
            "tournament": ["Friendly", "FIFA World Cup", "FIFA World Cup", "FIFA World Cup"],
            "city": ["x", "y", "Miami", "KC"],
            "country": ["X", "US", "US", "US"],
            "neutral": [False, True, False, False],
        }
    )


def test_played_matches_excludes_unplayed():
    p = played_matches(_sample_df())
    assert len(p) == 2
    assert set(p["home_team"]) == {"A", "Spain"}


def test_wc2026_fixtures_only_pending_worldcup():
    fx = wc2026_fixtures(_sample_df())
    assert set(fx["home_team"]) == {"Norway", "Argentina"}
    assert "Spain" not in set(fx["home_team"])  # disputado, não é fixture pendente
    assert "A" not in set(fx["home_team"])       # friendly antigo


def test_is_fresh(tmp_path):
    f = tmp_path / "c.csv"
    assert loader._is_fresh(f, 12) is False  # não existe
    f.write_text("x")
    assert loader._is_fresh(f, 12) is True
    os.utime(f, (time.time() - 13 * 3600, time.time() - 13 * 3600))
    assert loader._is_fresh(f, 12) is False  # velho demais


class _FakeResp:
    def __init__(self, text: str):
        self.text = text

    def raise_for_status(self):
        pass


def test_download_atomic_leaves_no_tmp(tmp_path, monkeypatch, make_settings):
    good = f"{_HEADER}\n2026-01-01,A,B,1,0,Friendly,x,X,False\n"
    monkeypatch.setattr(loader.httpx, "get", lambda *a, **k: _FakeResp(good))
    dest = tmp_path / "international_results.csv"
    loader._download(make_settings(cache_dir=tmp_path), dest)
    assert dest.exists()
    assert not (tmp_path / "international_results.csv.tmp").exists()


def test_download_bad_header_keeps_existing_cache(tmp_path, monkeypatch, make_settings):
    dest = tmp_path / "international_results.csv"
    dest.write_text(f"{_HEADER}\n2020-01-01,OLD,DATA,0,0,Friendly,x,X,False\n")
    monkeypatch.setattr(loader.httpx, "get", lambda *a, **k: _FakeResp("<html>rate limited</html>"))
    with pytest.raises(RuntimeError):
        loader._download(make_settings(cache_dir=tmp_path), dest)
    assert "OLD" in dest.read_text()  # cache bom permaneceu intacto


def test_load_results_validates_schema(tmp_path, monkeypatch, make_settings):
    dest = tmp_path / "international_results.csv"
    dest.write_text("foo,bar\n1,2\n")
    monkeypatch.setattr(loader, "_is_fresh", lambda *a, **k: True)  # não tenta baixar
    with pytest.raises(ValueError, match="colunas"):
        load_results(make_settings(cache_dir=tmp_path))


def test_load_results_parses_cached_csv(tmp_path, monkeypatch, make_settings):
    dest = tmp_path / "international_results.csv"
    dest.write_text(
        f"{_HEADER}\n"
        "2026-07-10,Spain,Belgium,2,1,FIFA World Cup,y,US,True\n"
        "2026-07-11,Norway,England,,,FIFA World Cup,Miami,US,False\n"
    )
    monkeypatch.setattr(loader, "_is_fresh", lambda *a, **k: True)
    df = load_results(make_settings(cache_dir=tmp_path))
    assert len(df) == 2
    assert str(df["date"].dtype).startswith("datetime")
    assert df["home_score"].isna().sum() == 1  # fixture pendente Norway×England


def test_load_results_falls_back_to_stale_cache(tmp_path, monkeypatch, make_settings):
    dest = tmp_path / "international_results.csv"
    dest.write_text(f"{_HEADER}\n2020-01-01,A,B,1,0,Friendly,x,X,False\n")  # cache velho válido

    def _boom(*a, **k):
        raise loader.httpx.ConnectError("sem rede")

    monkeypatch.setattr(loader.httpx, "get", _boom)
    # força tentar baixar; falha na rede; cai pro cache velho em vez de crashar
    df = load_results(make_settings(cache_dir=tmp_path), force_refresh=True)
    assert len(df) == 1


def test_load_results_no_cache_no_network_raises(tmp_path, monkeypatch, make_settings):
    def _boom(*a, **k):
        raise loader.httpx.ConnectError("sem rede")

    monkeypatch.setattr(loader.httpx, "get", _boom)
    with pytest.raises(RuntimeError):
        load_results(make_settings(cache_dir=tmp_path), force_refresh=True)
