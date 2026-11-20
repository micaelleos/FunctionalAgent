"""Diff por seção (títulos `##`) entre a página atual e a proposta (F20-RT-04).

Calculado no backend e guardado na proposta: o cartão mostra exatamente o que será escrito. Os dois
lados passam pelo mesmo conversor (storage → Markdown), para diferenças de formatação não virarem
mudança.
"""

from typing import Literal, TypedDict

Change = Literal["added", "removed", "changed"]
MAX_SIDE = 4000  # caracteres por lado de uma seção no cartão


class SectionDiff(TypedDict):
    section: str
    change: Change
    before: str
    after: str


def sections(markdown: str) -> list[tuple[str, str]]:
    """(título, corpo) na ordem; o que vem antes do 1º `##` é a seção "" (título e cabeçalho)."""
    out: list[tuple[str, list[str]]] = [("", [])]
    for line in markdown.replace("\r\n", "\n").split("\n"):
        if line.startswith("## "):
            out.append((line[3:].strip(), []))
        else:
            out[-1][1].append(line)
    return [
        (title, "\n".join(body).strip()) for title, body in out if title or "".join(body).strip()
    ]


def _norm(text: str) -> str:
    return "\n".join(" ".join(line.split()) for line in text.split("\n") if line.strip())


def _cut(text: str) -> str:
    return text if len(text) <= MAX_SIDE else text[:MAX_SIDE] + "\n…"


def section_diff(before: str, after: str) -> list[SectionDiff]:
    """Seções novas, removidas e alteradas, na ordem da página proposta (removidas no fim)."""
    old = dict(sections(before))
    new = sections(after)
    diff: list[SectionDiff] = []
    for title, body in new:
        if title not in old:
            diff.append(SectionDiff(section=title, change="added", before="", after=_cut(body)))
        elif _norm(old[title]) != _norm(body):
            diff.append(
                SectionDiff(
                    section=title, change="changed", before=_cut(old[title]), after=_cut(body)
                )
            )
    names = {title for title, _ in new}
    for title, body in sections(before):
        if title not in names:
            diff.append(SectionDiff(section=title, change="removed", before=_cut(body), after=""))
    return diff
