"""Testes da cadeia de fallback grátis (FallbackChatModel)."""

import pytest
from langchain_core.language_models import BaseChatModel
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage
from langchain_core.tools import tool
from pydantic import BaseModel

from deep_pitch.config.fallback import FallbackChatModel
from deep_pitch.config.models import get_model


def _fake(text: str) -> GenericFakeChatModel:
    return GenericFakeChatModel(messages=iter([AIMessage(text)]))


@tool
def _ping(x: str) -> str:
    """ping."""
    return x


def test_free_chain_is_basechatmodel(make_settings):
    s = make_settings(
        model_provider="free", free_chain="groq,google,nvidia",
        groq_api_key="a", google_api_key="b", nvidia_api_key="c",
    )
    m = get_model("main", s)
    assert isinstance(m, FallbackChatModel)
    assert isinstance(m, BaseChatModel)  # crítico: create_deep_agent exige isso
    assert len(m.models) == 3


def test_free_bind_tools_preserves_fallbacks(make_settings):
    s = make_settings(model_provider="free", free_chain="groq,google", groq_api_key="a", google_api_key="b")
    bound = get_model("main", s).bind_tools([_ping])
    assert len(getattr(bound, "fallbacks", [])) == 1  # 2 modelos → 1 fallback


def test_free_single_provider_returns_bare_model(make_settings):
    # só groq tem key → sem wrapper (nada pra cair)
    s = make_settings(model_provider="free", free_chain="groq,google,nvidia", groq_api_key="a")
    m = get_model("main", s)
    assert not isinstance(m, FallbackChatModel)
    assert type(m).__name__ == "ChatGroq"


def test_free_no_keys_raises(make_settings):
    s = make_settings(model_provider="free", free_chain="groq,nvidia,openrouter")
    with pytest.raises(ValueError):
        get_model("main", s)


def test_llm_type():
    assert FallbackChatModel(models=[_fake("x")])._llm_type == "fallback"


def test_generate_delegates_to_first_model():
    m = FallbackChatModel(models=[_fake("oi")])
    assert m.invoke("qualquer coisa").content == "oi"


def test_fallback_falls_through_on_error():
    # 1º modelo quebra na chamada → cai pro 2º
    class _Boom(GenericFakeChatModel):
        def _generate(self, *a, **k):
            raise RuntimeError("boom")

    m = FallbackChatModel(models=[_Boom(messages=iter([AIMessage("x")])), _fake("caiu-no-2")])
    assert m.invoke("hi").content == "caiu-no-2"


async def test_agenerate_delegates():
    m = FallbackChatModel(models=[_fake("async-oi")])
    result = await m.ainvoke("hi")
    assert result.content == "async-oi"


def test_with_structured_output_returns_runnable(make_settings):
    class Out(BaseModel):
        x: int

    # modelos reais (dummy key) — suportam with_structured_output no construct
    s = make_settings(model_provider="free", free_chain="groq,google", groq_api_key="a", google_api_key="b")
    assert get_model("main", s).with_structured_output(Out) is not None
