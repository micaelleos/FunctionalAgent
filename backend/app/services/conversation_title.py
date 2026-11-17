"""Título automático da conversa (F07-RF-04, F07-RT-05): uma chamada curta ao mesmo modelo."""

import re

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage

TITLE_MAX = 60
_QUOTES = "\"'\u201c\u201d\u2018\u2019*#"
PROVISIONAL_MAX = 60

TITLE_PROMPT = (
    "Dê um título curto (de 2 a 6 palavras, em português, sem aspas e sem ponto final) para uma "
    "conversa de especificação de software que começa com a mensagem abaixo. Responda só o "
    "título.\n\nMensagem:\n"
)


def provisional_title(text: str) -> str:
    """Enquanto o título gerado não chega (ou se a geração falhar): a 1ª mensagem truncada."""
    line = " ".join(text.split())
    return line if len(line) <= PROVISIONAL_MAX else line[: PROVISIONAL_MAX - 1].rstrip() + "…"


def clean_title(raw: str) -> str | None:
    lines = [line for line in raw.strip().splitlines() if line.strip()]
    if not lines:
        return None
    title = re.sub(r"^(t[íi]tulo\s*:\s*)", "", lines[0].strip(), flags=re.IGNORECASE)
    title = title.strip().strip(_QUOTES).strip().rstrip(".").strip()
    if not title:
        return None
    return title if len(title) <= TITLE_MAX else title[: TITLE_MAX - 1].rstrip() + "…"


async def generate_title(llm: BaseChatModel, first_message: str) -> tuple[str | None, BaseMessage]:
    """Título limpo (ou `None`) e a resposta crua, para contar os tokens no uso do turno."""
    response = await llm.ainvoke([HumanMessage(TITLE_PROMPT + first_message[:2000])])
    content = response.content
    text = (
        content
        if isinstance(content, str)
        else " ".join(str(p.get("text", "")) if isinstance(p, dict) else str(p) for p in content)
    )
    return clean_title(text), response
