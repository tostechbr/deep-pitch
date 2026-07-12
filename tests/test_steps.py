"""Testes da extração crua de passos (funções puras, sem personalização)."""

from deep_pitch.service.steps import Step, steps_from_update


class _AIMsg:
    """AIMessage-like: nome do agente + tool_calls."""

    def __init__(self, name, tool_calls):
        self.name = name
        self.tool_calls = tool_calls


def _update(agent, tools):
    calls = [{"name": t, "args": {}} for t in tools]
    return {"model": {"messages": [_AIMsg(agent, calls)]}}


def test_extracts_agent_and_tool_raw():
    steps = list(steps_from_update(0, _update("deep-pitch", ["write_todos", "task"])))
    assert steps == [
        Step(depth=0, agent="deep-pitch", tool="write_todos"),
        Step(depth=0, agent="deep-pitch", tool="task"),
    ]


def test_depth_comes_from_caller():
    steps = list(steps_from_update(1, _update("scout", ["web_search"])))
    assert steps[0].depth == 1
    assert steps[0].agent == "scout"


def test_skips_prediction_marshalling():
    steps = list(steps_from_update(0, _update("deep-pitch", ["reconcile", "Prediction"])))
    tools = [s.tool for s in steps]
    assert "reconcile" in tools
    assert "Prediction" not in tools  # saída estruturada não é passo


def test_message_without_tool_calls_yields_nothing():
    assert list(steps_from_update(0, _update("deep-pitch", []))) == []


def test_handles_dict_message():
    update = {"tools": {"messages": [{"name": "scout", "tool_calls": [{"name": "live_feed"}]}]}}
    steps = list(steps_from_update(1, update))
    assert steps == [Step(depth=1, agent="scout", tool="live_feed")]


def test_missing_agent_name_is_empty_not_error():
    steps = list(steps_from_update(0, {"model": {"messages": [_AIMsg(None, [{"name": "x"}])]}}))
    assert steps[0].agent == ""
    assert steps[0].tool == "x"
