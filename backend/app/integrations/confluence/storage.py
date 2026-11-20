"""Markdown → storage format do Confluence (F20-RT-03).

Determinístico (a mesma entrada gera o mesmo XHTML, então o hash da proposta vale para o que é
executado) e seguro: todo texto é escapado, nenhum HTML do conteúdo passa. Cobre o Markdown que o
agente escreve a partir dos modelos da metodologia: títulos, parágrafos, listas (aninhadas e
numeradas), tabelas, citações, blocos de código, `---`, negrito, itálico, riscado, código e links
`https`. Comentários `<!-- -->` dos modelos são instruções para o agente e não vão para a página.
"""

import re
from html import escape

_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_BULLET = re.compile(r"^(\s*)[-*+]\s+(.*)$")
_ORDERED = re.compile(r"^(\s*)\d+[.)]\s+(.*)$")
_TABLE_SEP = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*$")
_INLINE = re.compile(
    r"(`[^`]+`"
    r"|\*\*[^*]+\*\*"
    r"|~~[^~]+~~"
    r"|\[[^\]]+\]\(https://[^\s)]+\)"
    r"|(?<![\w*])\*[^*\s][^*]*\*(?![\w*])"
    r"|(?<![\w_])_[^_\s][^_]*_(?![\w_]))"
)
_LINK = re.compile(r"^\[([^\]]+)\]\((https://[^\s)]+)\)$")


def _inline(text: str) -> str:
    out: list[str] = []
    for part in _INLINE.split(text):
        if not part:
            continue
        if part.startswith("`") and part.endswith("`") and len(part) > 2:
            out.append(f"<code>{escape(part[1:-1])}</code>")
        elif part.startswith("**") and part.endswith("**") and len(part) > 4:
            out.append(f"<strong>{_inline(part[2:-2])}</strong>")
        elif part.startswith("~~") and part.endswith("~~") and len(part) > 4:
            out.append(f"<s>{_inline(part[2:-2])}</s>")
        elif link := _LINK.match(part):
            out.append(f'<a href="{escape(link[2], quote=True)}">{escape(link[1])}</a>')
        elif len(part) > 2 and part[0] == part[-1] and part[0] in "*_":
            out.append(f"<em>{_inline(part[1:-1])}</em>")
        else:
            out.append(escape(part, quote=False))
    return "".join(out)


def _cells(line: str) -> list[str]:
    row = line.strip()
    row = row[1:] if row.startswith("|") else row
    row = row[:-1] if row.endswith("|") and not row.endswith("\\|") else row
    return [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", row)]


def _table(lines: list[str]) -> str:
    header, *body = [_cells(line) for line in lines if not _TABLE_SEP.match(line)]
    rows = ["<tr>" + "".join(f"<th>{_inline(c)}</th>" for c in header) + "</tr>"]
    for cells in body:
        cells = (cells + [""] * len(header))[: len(header)]
        rows.append("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in cells) + "</tr>")
    return "<table><tbody>" + "".join(rows) + "</tbody></table>"


def _list(lines: list[str]) -> str:
    """Listas com aninhamento por indentação (2+ espaços por nível)."""
    items: list[tuple[int, bool, str]] = []
    for line in lines:
        match = _BULLET.match(line) or _ORDERED.match(line)
        if match is None:  # continuação do item anterior
            if items:
                depth, ordered, text = items[-1]
                items[-1] = (depth, ordered, f"{text} {line.strip()}")
            continue
        ordered = _ORDERED.match(line) is not None and _BULLET.match(line) is None
        items.append((len(match[1].expandtabs(2)) // 2, ordered, match[2]))
    return _render_items(items, 0)[0]


def _render_items(items: list[tuple[int, bool, str]], start: int) -> tuple[str, int]:
    depth, ordered, _ = items[start]
    tag = "ol" if ordered else "ul"
    out = [f"<{tag}>"]
    i = start
    while i < len(items) and items[i][0] >= depth:
        if items[i][0] > depth:
            nested, i = _render_items(items, i)
            out[-1] = out[-1].removesuffix("</li>") + nested + "</li>"
            continue
        out.append(f"<li>{_inline(items[i][2])}</li>")
        i += 1
    out.append(f"</{tag}>")
    return "".join(out), i


def _is_list(line: str) -> bool:
    return bool(_BULLET.match(line) or _ORDERED.match(line))


def markdown_to_storage(markdown: str) -> str:
    lines = _COMMENT.sub("", markdown.replace("\r\n", "\n")).split("\n")
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            i += 1
            continue
        if stripped.startswith("```"):
            code: list[str] = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code.append(lines[i])
                i += 1
            out.append(f"<pre>{escape(chr(10).join(code), quote=False)}</pre>")
            i += 1
            continue
        if heading := _HEADING.match(stripped):
            level = len(heading[1])
            out.append(f"<h{level}>{_inline(heading[2])}</h{level}>")
            i += 1
            continue
        if re.fullmatch(r"(-{3,}|\*{3,}|_{3,})", stripped):
            out.append("<hr />")
            i += 1
            continue
        if stripped.startswith("|") and i + 1 < len(lines) and _TABLE_SEP.match(lines[i + 1]):
            block = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                block.append(lines[i])
                i += 1
            out.append(_table(block))
            continue
        if stripped.startswith(">"):
            quote = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                quote.append(lines[i].strip()[1:].strip())
                i += 1
            out.append(f"<blockquote>{markdown_to_storage(chr(10).join(quote))}</blockquote>")
            continue
        if _is_list(line):
            block = []
            while (
                i < len(lines)
                and lines[i].strip()
                and (_is_list(lines[i]) or lines[i].startswith((" ", "\t")))
            ):
                block.append(lines[i])
                i += 1
            out.append(_list(block))
            continue
        paragraph = []
        while i < len(lines) and lines[i].strip() and not _starts_block(lines, i):
            paragraph.append(lines[i].strip())
            i += 1
        out.append(f"<p>{'<br />'.join(_inline(p) for p in paragraph)}</p>")
    return "".join(out)


def _starts_block(lines: list[str], i: int) -> bool:
    stripped = lines[i].strip()
    return bool(
        stripped.startswith(("```", ">", "#"))
        or _is_list(lines[i])
        or (stripped.startswith("|") and i + 1 < len(lines) and _TABLE_SEP.match(lines[i + 1]))
    )
