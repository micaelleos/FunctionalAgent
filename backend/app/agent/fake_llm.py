"""Modelos de chat sem rede: roteirizado (testes e evals offline) e eco (`make dev` sem GCP)."""

from collections.abc import Callable, Iterator, Sequence
from typing import Any

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel, LanguageModelInput
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage, HumanMessage
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool
from pydantic import Field

Script = Callable[[Sequence[BaseMessage]], AIMessage]


def _chunks(message: AIMessage) -> Iterator[ChatGenerationChunk]:
    """Divide o texto em pedaços (streaming de verdade nos testes) e manda as tool calls no fim."""
    text = message.content if isinstance(message.content, str) else ""
    words = text.split(" ")
    for i, word in enumerate(words):
        piece = word if i == len(words) - 1 else word + " "
        if piece:
            yield ChatGenerationChunk(message=AIMessageChunk(content=piece))
    yield ChatGenerationChunk(
        message=AIMessageChunk(
            content="",
            tool_call_chunks=[
                {"name": c["name"], "args": _json(c["args"]), "id": c["id"], "index": i}
                for i, c in enumerate(message.tool_calls)
            ],
            usage_metadata=message.usage_metadata,
        )
    )


def _json(args: dict[str, Any]) -> str:
    import json

    return json.dumps(args, ensure_ascii=False)


class ScriptedChatModel(BaseChatModel):
    """Devolve as respostas de `responses` em ordem; cada item é uma `AIMessage` ou uma função das
    mensagens recebidas. Grava as entradas de cada chamada em `calls`."""

    responses: list[Any]  # AIMessage ou Script (Any: o validador do AIMessage não aceita funções)
    calls: list[list[BaseMessage]] = Field(default_factory=list)
    bound_tools: list[str] = Field(default_factory=list)

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def bind_tools(
        self, tools: Sequence[Any], *, tool_choice: str | None = None, **kwargs: Any
    ) -> Runnable[LanguageModelInput, AIMessage]:
        self.bound_tools = [
            t.name if isinstance(t, BaseTool) else str(t["function"]["name"]) for t in tools
        ]
        return self

    def _next(self, messages: list[BaseMessage]) -> AIMessage:
        self.calls.append(list(messages))
        if not self.responses:
            raise AssertionError("roteiro do LLM acabou")
        item = self.responses.pop(0)
        message: AIMessage = item(messages) if callable(item) else item
        if message.usage_metadata is None:
            message = message.model_copy(
                update={
                    "usage_metadata": {
                        "input_tokens": 100,
                        "output_tokens": 20,
                        "total_tokens": 120,
                    }
                }
            )
        return message

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        return ChatResult(generations=[ChatGeneration(message=self._next(messages))])

    def _stream(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        yield from _chunks(self._next(messages))


class EchoChatModel(ScriptedChatModel):
    """Responde repetindo a última mensagem do usuário (desenvolvimento local sem Vertex AI)."""

    responses: list[Any] = Field(default_factory=list)

    def _next(self, messages: list[BaseMessage]) -> AIMessage:
        last = next((m for m in reversed(messages) if isinstance(m, HumanMessage)), None)
        text = last.content if last is not None and isinstance(last.content, str) else ""
        return AIMessage(
            content=f"(modelo local de eco) Você disse: {text}",
            usage_metadata={"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
        )
