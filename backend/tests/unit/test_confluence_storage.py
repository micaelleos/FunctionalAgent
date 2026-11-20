"""Markdown → storage format (F20-RT-03): determinístico, escapado, ida e volta com a F19."""

import pytest

from app.integrations.confluence.markdown import storage_to_markdown
from app.integrations.confluence.storage import markdown_to_storage

DOC = """# Glossário — Loja

<!-- instrução do modelo para o agente -->

Termos com **um** significado e `código`, *ênfase*, ~~revogado~~ e [link](https://x.atlassian.net/wiki/a).

| Termo | Definição |
|---|---|
| Pedido | compra **confirmada** |
| Cliente | quem compra |

- item 1
  - filho
- item 2

1. um
2. dois

> citação

```
code <b>
```

---
"""


@pytest.mark.req("F20-RT-03")
def test_converte_o_markdown_dos_modelos() -> None:
    storage = markdown_to_storage(DOC)
    assert storage.startswith("<h1>Glossário — Loja</h1><p>Termos com <strong>um</strong>")
    assert "instrução do modelo" not in storage
    assert "<code>código</code>" in storage
    assert "<em>ênfase</em>" in storage
    assert "<s>revogado</s>" in storage
    assert '<a href="https://x.atlassian.net/wiki/a">link</a>' in storage
    assert "<tr><th>Termo</th><th>Definição</th></tr>" in storage
    assert "<td>compra <strong>confirmada</strong></td>" in storage
    assert "<ul><li>item 1<ul><li>filho</li></ul></li><li>item 2</li></ul>" in storage
    assert "<ol><li>um</li><li>dois</li></ol>" in storage
    assert "<blockquote><p>citação</p></blockquote>" in storage
    assert "<pre>code &lt;b&gt;</pre>" in storage
    assert storage.endswith("<hr />")


@pytest.mark.req("F20-RT-03")
def test_deterministico_e_escapa_html() -> None:
    evil = 'Olá <script>alert(1)</script> & [x](javascript:alert(1)) <ac:macro ac:name="x"/>'
    storage = markdown_to_storage(evil)
    assert markdown_to_storage(evil) == storage
    assert "<script>" not in storage
    assert "<ac:" not in storage
    assert "&lt;script&gt;" in storage
    assert "&amp;" in storage
    assert "href" not in storage  # só links https viram <a>


@pytest.mark.req("F20-RT-03")
def test_ida_e_volta_com_o_conversor_da_f19() -> None:
    back = storage_to_markdown(markdown_to_storage(DOC))
    for text in ("Glossário — Loja", "Pedido", "compra", "item 1", "filho", "citação", "code <b>"):
        assert text in back
    assert markdown_to_storage(back) == markdown_to_storage(back)
