"""Storage format do Confluence (XHTML) → Markdown para o modelo (F19-RT-06).

Só a biblioteca padrão (`html.parser`). Cobre títulos, parágrafos, listas, tabelas, código, links,
ênfase e as macros comuns (info/note/warning/status/code como texto); macro desconhecida vira
`[macro: nome]`. O resultado é truncado (F19-RT-04).
"""

from html.parser import HTMLParser

MAX_CHARS = 8000
TRUNCATED = "\n\n… (página truncada: leia o restante no Confluence)"
_BLOCK = {"p", "div", "br", "hr", "blockquote", "pre"}
_TEXT_MACROS = {"info", "note", "warning", "tip", "panel", "expand", "excerpt", "section", "column"}
_SKIP_MACROS = {"toc", "children", "pagetree", "recently-updated", "contributors", "anchor"}


class _Parser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self.lists: list[str] = []  # "ul" / "ol"
        self.counters: list[int] = []
        self.href: str | None = None
        self.link_text: list[str] = []
        self.row: list[str] | None = None
        self.cell: list[str] | None = None
        self.rows: list[list[str]] = []
        self.header_cols = 0
        self.skip = 0  # dentro de macro ignorada
        self.pre = False
        self.macro_names: list[str] = []
        self.param = False

    # ---- utilidades
    def _emit(self, text: str) -> None:
        if self.skip or self.param:
            return
        if self.href is not None:
            self.link_text.append(text)
        elif self.cell is not None:
            self.cell.append(text)
        else:
            self.out.append(text)

    def _newline(self, n: int = 1) -> None:
        if self.cell is not None:
            self.cell.append(" ")
            return
        self.out.append("\n" * n)

    # ---- tags
    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = dict(attrs)
        if tag == "ac:structured-macro":
            name = (a.get("ac:name") or "").lower()
            self.macro_names.append(name)
            if self.skip or name in _SKIP_MACROS:
                self.skip += 1
            elif name == "status":
                self._emit("[status: ")
            elif name == "code":
                self.pre = True
                self._newline(2)
                self._emit("```\n")
            elif name not in _TEXT_MACROS:
                self._emit(f"[macro: {name}]")
                self.skip += 1
            elif name in {"info", "note", "warning", "tip"}:
                self._newline(2)
                self._emit(f"> **{name.capitalize()}:** ")
            return
        if tag == "ac:parameter":
            # O título da macro de status é o texto dela; os outros parâmetros não aparecem.
            macro = self.macro_names[-1] if self.macro_names else ""
            self.param = not (macro == "status" and (a.get("ac:name") or "") == "title")
            return
        if self.skip:
            return
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self._newline(2)
            self._emit("#" * int(tag[1]) + " ")
        elif tag in _BLOCK:
            self._newline(2 if tag != "br" else 1)
            if tag == "pre":
                self.pre = True
                self._emit("```\n")
        elif tag in {"ul", "ol"}:
            if not self.lists:
                self._newline()
            self.lists.append(tag)
            self.counters.append(0)
        elif tag == "li":
            indent = "  " * (len(self.lists) - 1)
            if self.lists and self.lists[-1] == "ol":
                self.counters[-1] += 1
                marker = f"{self.counters[-1]}."
            else:
                marker = "-"
            self._newline()
            self._emit(f"{indent}{marker} ")
        elif tag in {"strong", "b"}:
            self._emit("**")
        elif tag in {"em", "i"}:
            self._emit("_")
        elif tag == "code" and not self.pre:
            self._emit("`")
        elif tag == "a":
            href = a.get("href") or ""
            self.href = href if href.startswith(("https://", "http://", "/")) else ""
            self.link_text = []
        elif tag == "ri:page":
            title = a.get("ri:content-title")
            if title:
                self._emit(title)
        elif tag == "table":
            self.rows = []
            self.header_cols = 0
        elif tag == "tr":
            self.row = []
        elif tag in {"td", "th"}:
            self.cell = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "ac:structured-macro":
            name = self.macro_names.pop() if self.macro_names else ""
            if self.skip:
                self.skip -= 1
                return
            if name == "status":
                self._emit("]")
            elif name == "code":
                self._emit("\n```")
                self.pre = False
                self._newline(2)
            return
        if tag == "ac:parameter":
            self.param = False
            return
        if self.skip:
            return
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6", "p", "div", "blockquote"}:
            self._newline(2)
        elif tag == "pre":
            self._emit("\n```")
            self.pre = False
            self._newline(2)
        elif tag in {"ul", "ol"}:
            if self.lists:
                self.lists.pop()
                self.counters.pop()
            if not self.lists:
                self._newline()
        elif tag in {"strong", "b"}:
            self._emit("**")
        elif tag in {"em", "i"}:
            self._emit("_")
        elif tag == "code" and not self.pre:
            self._emit("`")
        elif tag == "a" and self.href is not None:
            text = "".join(self.link_text).strip()
            href = self.href
            self.href = None
            self._emit(f"[{text or href}]({href})" if href else text)
        elif tag in {"td", "th"} and self.cell is not None and self.row is not None:
            self.row.append(" ".join("".join(self.cell).split()).replace("|", "\\|"))
            self.cell = None
        elif tag == "tr" and self.row is not None:
            self.rows.append(self.row)
            self.row = None
        elif tag == "table":
            self._table()

    def _table(self) -> None:
        rows = [r for r in self.rows if r]
        self.rows = []
        if not rows:
            return
        width = max(len(r) for r in rows)
        lines = []
        for i, r in enumerate(rows):
            cells = r + [""] * (width - len(r))
            lines.append("| " + " | ".join(cells) + " |")
            if i == 0:
                lines.append("|" + "---|" * width)
        self._newline(2)
        self.out.append("\n".join(lines))
        self._newline(2)

    def handle_data(self, data: str) -> None:
        if self.pre:
            self._emit(data)
        else:
            text = " ".join(data.split())
            if text:
                lead = " " if data[:1].isspace() else ""
                trail = " " if data[-1:].isspace() else ""
                self._emit(f"{lead}{text}{trail}")


def storage_to_markdown(storage: str, limit: int = MAX_CHARS) -> str:
    parser = _Parser()
    try:
        parser.feed(storage)
        parser.close()
    except Exception:  # XHTML malformado: devolve o texto sem tags
        return " ".join(storage.split())[:limit]
    text = "".join(parser.out)
    lines = [line.rstrip() for line in text.splitlines()]
    cleaned: list[str] = []
    for line in lines:
        if not line.strip() and (not cleaned or not cleaned[-1].strip()):
            continue
        cleaned.append(line)
    result = "\n".join(cleaned).strip()
    return result if len(result) <= limit else result[:limit].rstrip() + TRUNCATED
