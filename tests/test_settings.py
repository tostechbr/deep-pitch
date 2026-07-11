"""Testes da Settings."""


def test_defaults(make_settings):
    s = make_settings()
    assert s.model_provider == "anthropic"
    assert s.cache_ttl_hours == 12
    assert s.history_years == 8
    assert s.football_data_competition == "WC"
    assert s.langsmith_tracing is False


def test_free_chain_list_parse(make_settings):
    s = make_settings(free_chain=" groq, google ,nvidia,")
    assert s.free_chain_list == ["groq", "google", "nvidia"]


def test_free_chain_list_default(make_settings):
    assert make_settings().free_chain_list == ["groq", "google", "nvidia", "openrouter"]
