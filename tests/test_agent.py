"""Smoke test de montagem do agente (dummy key — sem chamada de rede)."""

from deep_pitch.agent import build_agent
from deep_pitch.subagents import historian_subagent, scout_subagent


def test_scout_wiring(make_settings):
    s = make_settings(model_provider="anthropic", anthropic_api_key="dummy")
    scout = scout_subagent(s)
    assert scout["name"] == "scout"
    assert {t.name for t in scout["tools"]} == {"web_search", "live_feed"}


def test_historian_wiring(make_settings):
    s = make_settings(model_provider="anthropic", anthropic_api_key="dummy")
    hist = historian_subagent(s)
    assert hist["name"] == "historian"
    assert {t.name for t in hist["tools"]} == {"baseline_prediction", "head_to_head"}


def test_build_agent_constructs(make_settings):
    # construção completa (main + subagents + tools + response_format), sem invoke
    agent = build_agent(make_settings(model_provider="anthropic", anthropic_api_key="dummy"))
    assert hasattr(agent, "invoke")
