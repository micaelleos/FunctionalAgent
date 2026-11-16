"""Markdown ⇄ ADF (Atlassian Document Format, Jira API v3) — F05-RT-05.

`markdown_to_adf` cobre títulos, parágrafos, listas (com e sem número), negrito, itálico, código
(inline e bloco), tabelas, links e quebras de linha. `adf_to_markdown` faz o caminho de volta para
o agente ler descrições do Jira e para avaliar a prontidão de issues existentes (F05-RF-12).
Fica em `agent/spec` (e não em `integrations/jira`) porque o renderizador do agente o usa e as
camadas irmãs não se importam (import-linter).
"""

from typing import Any

from markdown_it import MarkdownIt
from markdown_it.token import Token

Node = dict[str, Any]

_MD = MarkdownIt("commonmark", {"html": False}).enable("table").enable("strikethrough")
_MARKS = {"strong": "strong", "em": "em", "s": "strike"}
_SAFE_SCHEMES = ("http://", "https://", "mailto:")


# ------------------------------------------------------------------ Markdown → ADF


def _text(text: str, marks: list[Node]) -> Node:
    node: Node = {"type": "text", "text": text}
    if marks:
        node["marks"] = [dict(m) for m in marks]
    return node


def _inline(tokens: list[Token]) -> list[Node]:
    out: list[Node] = []
    marks: list[Node] = []
    for tok in tokens:
        kind = tok.type
        if kind == "text" and tok.content:
            out.append(_text(tok.content, marks))
        elif kind == "code_inline":
            out.append(_text(tok.content, [*marks, {"type": "code"}]))
        elif kind in ("softbreak", "hardbreak"):
            out.append({"type": "hardBreak"})
        elif kind.endswith("_open") and kind[:-5] in _MARKS:
            marks.append({"type": _MARKS[kind[:-5]]})
        elif kind.endswith("_close") and kind[:-6] in _MARKS:
            name = _MARKS[kind[:-6]]
            for i in range(len(marks) - 1, -1, -1):
                if marks[i]["type"] == name:
                    del marks[i]
                    break
        elif kind == "link_open":
            href = str(tok.attrs.get("href", ""))
            # Só esquemas seguros viram link; o resto fica como texto.
            if href.startswith(_SAFE_SCHEMES):
                marks.append({"type": "link", "attrs": {"href": href}})
            else:
                marks.append({"type": "_nolink"})
        elif kind == "link_close":
            for i in range(len(marks) - 1, -1, -1):
                if marks[i]["type"] in ("link", "_nolink"):
                    del marks[i]
                    break
    for node in out:
        if "marks" in node:
            node["marks"] = [m for m in node["marks"] if m["type"] != "_nolink"] or None
            if node["marks"] is None:
                del node["marks"]
    return out


def inline_to_adf(text: str) -> list[Node]:
    """Converte uma linha de Markdown em nós inline de ADF (para itens de lista e parágrafos)."""
    tokens = _MD.parseInline(text)
    return _inline(tokens[0].children or []) if tokens else []


def _paragraph(content: list[Node]) -> Node:
    return {"type": "paragraph", "content": content} if content else {"type": "paragraph"}


def _blocks(tokens: list[Token], i: int, end: str | None) -> tuple[list[Node], int]:
    """Lê blocos até o token de fechamento `end` (ou o fim); devolve os nós e a posição."""
    out: list[Node] = []
    while i < len(tokens):
        tok = tokens[i]
        if end is not None and tok.type == end:
            return out, i + 1
        if tok.type == "heading_open":
            level = min(int(tok.tag[1]), 6)
            inline = tokens[i + 1].children or []
            out.append({"type": "heading", "attrs": {"level": level}, "content": _inline(inline)})
            i += 3
        elif tok.type == "paragraph_open":
            out.append(_paragraph(_inline(tokens[i + 1].children or [])))
            i += 3
        elif tok.type in ("bullet_list_open", "ordered_list_open"):
            kind = "bulletList" if tok.type == "bullet_list_open" else "orderedList"
            close = tok.type.replace("_open", "_close")
            items: list[Node] = []
            i += 1
            while tokens[i].type != close:
                content, i = _blocks(tokens, i + 1, "list_item_close")
                items.append({"type": "listItem", "content": content or [_paragraph([])]})
            out.append({"type": kind, "content": items})
            i += 1
        elif tok.type in ("fence", "code_block"):
            node: Node = {"type": "codeBlock", "content": []}
            if tok.info.strip():
                node["attrs"] = {"language": tok.info.strip().split()[0]}
            code = tok.content.rstrip("\n")
            if code:
                node["content"] = [{"type": "text", "text": code}]
            out.append(node)
            i += 1
        elif tok.type == "blockquote_open":
            content, i = _blocks(tokens, i + 1, "blockquote_close")
            out.append({"type": "blockquote", "content": content})
        elif tok.type == "hr":
            out.append({"type": "rule"})
            i += 1
        elif tok.type == "table_open":
            table, i = _table(tokens, i + 1)
            out.append(table)
        else:
            i += 1
    return out, i


def _table(tokens: list[Token], i: int) -> tuple[Node, int]:
    rows: list[Node] = []
    header = False
    cells: list[Node] = []
    while tokens[i].type != "table_close":
        tok = tokens[i]
        if tok.type == "thead_open":
            header = True
        elif tok.type == "tbody_open":
            header = False
        elif tok.type == "tr_open":
            cells = []
        elif tok.type in ("th_open", "td_open"):
            kind = "tableHeader" if header else "tableCell"
            content = _inline(tokens[i + 1].children or [])
            cells.append({"type": kind, "content": [_paragraph(content)]})
            i += 2
        elif tok.type == "tr_close":
            rows.append({"type": "tableRow", "content": cells})
        i += 1
    return {"type": "table", "content": rows}, i + 1


def markdown_to_adf(markdown: str) -> Node:
    content, _ = _blocks(_MD.parse(markdown), 0, None)
    return {"type": "doc", "version": 1, "content": content}


# ------------------------------------------------------------------ ADF → Markdown


def _md_inline(nodes: list[Node]) -> str:
    out = []
    for node in nodes:
        kind = node.get("type")
        if kind == "hardBreak":
            out.append("\n")
            continue
        if kind in ("mention", "emoji", "inlineCard", "status", "date"):
            attrs = node.get("attrs", {})
            out.append(str(attrs.get("text") or attrs.get("url") or attrs.get("shortName") or ""))
            continue
        text = str(node.get("text", ""))
        for mark in node.get("marks", []):
            mtype = mark.get("type")
            if mtype == "code":
                text = f"`{text}`"
            elif mtype == "strong":
                text = f"**{text}**"
            elif mtype == "em":
                text = f"*{text}*"
            elif mtype == "strike":
                text = f"~~{text}~~"
            elif mtype == "link":
                text = f"[{text}]({mark.get('attrs', {}).get('href', '')})"
        out.append(text)
    return "".join(out)


def _md_block(node: Node, indent: str = "") -> str:
    kind = node.get("type")
    content: list[Node] = node.get("content", [])
    if kind == "heading":
        level = int(node.get("attrs", {}).get("level", 2))
        return f"{'#' * level} {_md_inline(content)}"
    if kind == "paragraph":
        return _md_inline(content)
    if kind in ("bulletList", "orderedList"):
        lines = []
        for n, item in enumerate(content, start=1):
            bullet = "-" if kind == "bulletList" else f"{n}."
            parts = [_md_block(child, indent + "  ") for child in item.get("content", [])]
            body = "\n".join(p for p in parts if p).replace("\n", "\n" + indent + "  ")
            lines.append(f"{indent}{bullet} {body}")
        return "\n".join(lines)
    if kind == "codeBlock":
        lang = node.get("attrs", {}).get("language", "")
        return f"```{lang}\n{_md_inline(content)}\n```"
    if kind == "blockquote":
        inner = "\n\n".join(_md_block(c) for c in content)
        return "\n".join(f"> {line}" for line in inner.splitlines())
    if kind == "rule":
        return "---"
    if kind == "table":
        rows = []
        for r, row in enumerate(content):
            cells = [_md_inline_cells(c) for c in row.get("content", [])]
            rows.append("| " + " | ".join(cells) + " |")
            if r == 0:
                rows.append("|" + "---|" * len(cells))
        return "\n".join(rows)
    if kind in ("panel", "expand", "nestedExpand", "layoutSection", "layoutColumn"):
        return "\n\n".join(_md_block(c) for c in content)
    return _md_inline(content) if content else ""


def _md_inline_cells(cell: Node) -> str:
    return " ".join(_md_block(c) for c in cell.get("content", [])).replace("\n", " ")


def adf_to_markdown(doc: Node | None) -> str:
    if not doc or not isinstance(doc, dict):
        return ""
    blocks = [_md_block(n) for n in doc.get("content", [])]
    return "\n\n".join(b for b in blocks if b).strip()
