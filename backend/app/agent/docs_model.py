"""Modelo do espaço de documentação (F20-RT-05, docs/metodologia/espaco-confluence.md).

Os modelos de página vêm de `docs/metodologia/modelos/` (copiados em `templates/confluence/`, com
teste de sincronia). Início, Arquitetura, Registro de mudanças e as páginas-pai têm esqueletos
curtos aqui. Nada disto fala com o Confluence: é a forma das páginas.
"""

from dataclasses import dataclass
from importlib import resources

LABEL = "specflow"
LABEL_PREFIX = "specflow-tipo-"

# Tipo → arquivo do modelo (os que a metodologia define).
TEMPLATE_FILES = {
    "constituicao": "constituicao.md",
    "glossario": "glossario.md",
    "regras": "regra-de-negocio.md",
    "roadmap": "roadmap.md",
    "feature": "feature.md",
    "adr": "adr.md",
}

_SKELETONS = {
    "inicio": (
        "# <Projeto> — Documentação\n\n"
        "<!-- Visão do produto, público e links. -->\n\n"
        "## Visão\n<Para quem é o produto e o problema que resolve.>\n\n"
        "## Links\n- **Projeto Jira:** <CHAVE>\n- **SpecFlow:** https://specsflow-ai.web.app\n"
    ),
    "arquitetura": (
        "# Arquitetura — <Projeto>\n\n"
        "## Visão geral\n<Componentes e como conversam.>\n\n"
        "## Integrações\n<Sistemas externos e contratos.>\n\n"
        "## Onde fica cada coisa\n<Repositórios, serviços, dados.>\n"
    ),
    "registro": (
        "# Registro de mudanças\n\n"
        "Uma linha por escrita do SpecFlow, na mesma confirmação.\n\n"
        "| Data | Página | Resumo | Autor |\n|---|---|---|---|\n"
    ),
    "adr-indice": (
        "# Decisões (ADR)\n\nUma página filha por decisão: `ADR-nnn — <título>`. "
        "Uma ADR aceita não é editada; uma decisão nova a substitui.\n"
    ),
    "feature-indice": (
        "# Features\n\nUma página filha por épico: `FEAT-nn — <nome>`, "
        "com a chave do épico no Jira.\n"
    ),
}

# Tipos que o agente pode criar ou atualizar (o Registro é escrito pela confirmação).
WRITABLE = ("constituicao", "glossario", "regras", "arquitetura", "adr", "roadmap", "feature")
# Uma página por espaço; ADRs e features são filhas das páginas-pai.
SINGLETONS = ("constituicao", "glossario", "regras", "arquitetura", "roadmap")


@dataclass(frozen=True)
class SpacePage:
    ref: str
    title: str
    kind: str  # rótulo `specflow-tipo-<kind>`
    template: str  # chave do esqueleto (tipo ou `*-indice`)
    parent: str | None = None  # ref da página-pai; `None` = página inicial do espaço


# Árvore do modelo, pai antes do filho. "Início" é a página inicial que o Confluence cria junto
# com o espaço.
SPACE_TREE = (
    SpacePage("inicio", "Início", "inicio", "inicio"),
    SpacePage("constituicao", "Constituição", "constituicao", "constituicao", "inicio"),
    SpacePage("glossario", "Glossário", "glossario", "glossario", "inicio"),
    SpacePage("regras", "Regras de negócio", "regras", "regras", "inicio"),
    SpacePage("arquitetura", "Arquitetura", "arquitetura", "arquitetura", "inicio"),
    SpacePage("adr", "Decisões (ADR)", "adr", "adr-indice", "inicio"),
    SpacePage("roadmap", "Roadmap", "roadmap", "roadmap", "inicio"),
    SpacePage("feature", "Features", "feature", "feature-indice", "inicio"),
    SpacePage("registro", "Registro de mudanças", "registro", "registro", "inicio"),
)


def labels_for(kind: str) -> list[str]:
    return [LABEL, f"{LABEL_PREFIX}{kind}"]


def template(key: str) -> str:
    """Esqueleto em Markdown de um tipo (ou página-pai), ainda com os campos `<…>`."""
    if key in _SKELETONS:
        return _SKELETONS[key]
    return (
        resources.files("app.agent.templates.confluence")
        .joinpath(TEMPLATE_FILES[key])
        .read_text("utf-8")
    )


def fill(markdown: str, project: str, key: str) -> str:
    return markdown.replace("<Projeto>", project).replace("<CHAVE>", key)
