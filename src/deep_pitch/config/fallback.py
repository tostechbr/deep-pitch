"""FallbackChatModel — cadeia de fallback que É um BaseChatModel.

Por quê existe: create_deep_agent aceita `str | BaseChatModel`. O
RunnableWithFallbacks (o que .with_fallbacks() devolve) NÃO é um BaseChatModel,
então é mal-interpretado como string de spec de modelo e quebra
(`spec.count(":")`).

Este wrapper é um BaseChatModel de verdade (passa no isinstance) mas delega
TODO o trabalho real — inclusive bind_tools e with_structured_output — ao
.with_fallbacks() do langchain-core, que já lida com a cadeia corretamente
(mapeia bind_tools sobre primário + fallbacks). Ou seja: casca fina só pra
satisfazer o tipo; a lógica de fallback é a nativa e testada do LangChain.
"""

from __future__ import annotations

from typing import Any

from langchain_core.language_models import BaseChatModel, LanguageModelInput
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import Runnable


class FallbackChatModel(BaseChatModel):
    """Tenta os modelos na ordem; cai pro próximo em erro (rate limit, down)."""

    models: list[BaseChatModel]

    @property
    def _llm_type(self) -> str:
        return "fallback"

    @property
    def _chain(self) -> Runnable:
        """Cadeia nativa do LangChain que faz o fallback de verdade."""
        if len(self.models) == 1:
            return self.models[0]
        return self.models[0].with_fallbacks(self.models[1:])

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        msg = self._chain.invoke(messages, stop=stop, **kwargs)
        return ChatResult(generations=[ChatGeneration(message=msg)])

    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        msg = await self._chain.ainvoke(messages, stop=stop, **kwargs)
        return ChatResult(generations=[ChatGeneration(message=msg)])

    def bind_tools(self, tools, **kwargs) -> Runnable[LanguageModelInput, BaseMessage]:
        return self._chain.bind_tools(tools, **kwargs)

    def with_structured_output(self, schema, **kwargs) -> Runnable[LanguageModelInput, Any]:
        return self._chain.with_structured_output(schema, **kwargs)
