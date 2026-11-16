"""Verificação de prontidão para agente de código (doc 10 §4.4, F05-RT-14, F05-RT-15).

Função pura, sem LLM: recebe a spec e os parâmetros versionados (`prompts/readiness_v1.json`)
e diz quais regras passam. Avisa, não bloqueia (RA-22): o resultado acompanha a proposta e decide
só a label `agent-ready`.
"""

import json
import re
from dataclasses import dataclass
from enum import StrEnum
from functools import cache
from importlib import resources

from pydantic import BaseModel, ConfigDict

from app.agent.spec.render import to_markdown
from app.agent.spec.schema import EpicSpec, ScenarioKind, WorkItemSpec

LABEL_SPECFLOW = "specflow"
LABEL_AGENT_READY = "agent-ready"
LABEL_HUMAN_ONLY = "human-only"


class VagueTerm(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    term: str
    # "melhorar" só é vago sem um número na mesma frase ("melhorar o p95 para 300 ms" é concreto).
    unless_number: bool = False


class ReadinessConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    version: str
    title_min_words: int
    title_max_words: int
    max_criteria: int
    max_body_words: int
    min_body_words_with_link: int
    vague_terms: tuple[VagueTerm, ...]
    link_only_phrases: tuple[str, ...]
    # RA-24: indícios de mudança sensível; o agente confirma se a spec é `human_only`.
    sensitive_terms: tuple[str, ...] = ()


@cache
def load_config(version: str = "v1") -> ReadinessConfig:
    raw = (
        resources.files("app.agent.prompts")
        .joinpath(f"readiness_{version}.json")
        .read_text("utf-8")
    )
    return ReadinessConfig.model_validate(json.loads(raw))


class Severity(StrEnum):
    REQUIRED = "obrigatória"
    WARNING = "aviso"


@dataclass(frozen=True)
class RuleResult:
    id: str
    label: str
    severity: Severity
    passed: bool
    detail: str = ""


@dataclass(frozen=True)
class Readiness:
    config_version: str
    results: tuple[RuleResult, ...]

    @property
    def ready(self) -> bool:
        """Pronta para agente: todas as regras obrigatórias passam (avisos não contam)."""
        return all(r.passed for r in self.results if r.severity is Severity.REQUIRED)

    @property
    def missing(self) -> tuple[RuleResult, ...]:
        return tuple(r for r in self.results if not r.passed and r.severity is Severity.REQUIRED)

    @property
    def warnings(self) -> tuple[RuleResult, ...]:
        return tuple(r for r in self.results if not r.passed and r.severity is Severity.WARNING)


_WORD = re.compile(r"[\wÀ-ÿ'-]+")
_INFINITIVE = re.compile(r"^[a-zà-ÿ]{2,}(ar|er|ir|or|ôr)$")
_URL = re.compile(r"https?://\S+")
_SENTENCE = re.compile(r"[^.!?\n]+")


def _words(text: str) -> list[str]:
    return _WORD.findall(text)


def _p01_title(spec: WorkItemSpec | EpicSpec, cfg: ReadinessConfig) -> RuleResult:
    words = _words(spec.title)
    problems = []
    if not cfg.title_min_words <= len(words) <= cfg.title_max_words:
        problems.append(
            f"{len(words)} palavras (esperado de {cfg.title_min_words} a {cfg.title_max_words})"
        )
    if not words or not _INFINITIVE.match(words[0].lower()):
        problems.append("não começa com verbo no infinitivo")
    return RuleResult(
        "P-01",
        "Título de ação, de 5 a 20 palavras",
        Severity.REQUIRED,
        not problems,
        "; ".join(problems),
    )


def _p02_objective(spec: WorkItemSpec | EpicSpec) -> RuleResult:
    return RuleResult("P-02", "Objetivo", Severity.REQUIRED, bool(spec.objective))


def _p03_criteria(spec: WorkItemSpec, cfg: ReadinessConfig) -> RuleResult:
    count = len(spec.acceptance_criteria)
    incomplete = [s.id for s in spec.acceptance_criteria if not (s.given and s.when and s.then)]
    problems = []
    if not 1 <= count <= cfg.max_criteria:
        problems.append(f"{count} critérios (esperado de 1 a {cfg.max_criteria})")
    if incomplete:
        problems.append(f"sem Dado/Quando/Então completo: {', '.join(incomplete)}")
    label = f"De 1 a {cfg.max_criteria} critérios de aceite com Dado/Quando/Então"
    return RuleResult("P-03", label, Severity.REQUIRED, not problems, "; ".join(problems))


def _p03_epic(spec: EpicSpec) -> RuleResult:
    # Épico (RA-11): critérios do épico e decomposição em histórias.
    problems = []
    if not spec.acceptance_criteria:
        problems.append("sem critérios de aceite do épico")
    if not spec.decomposition:
        problems.append("sem decomposição em histórias")
    label = "Critérios de aceite do épico e decomposição"
    return RuleResult("P-03", label, Severity.REQUIRED, not problems, "; ".join(problems))


def _p04_error_case(spec: WorkItemSpec) -> RuleResult:
    kinds = {s.kind for s in spec.acceptance_criteria}
    ok = bool(kinds & {ScenarioKind.ERRO, ScenarioKind.BORDA})
    return RuleResult("P-04", "Cenário de erro ou de borda", Severity.REQUIRED, ok)


def _p05_out_of_scope(spec: WorkItemSpec | EpicSpec) -> RuleResult:
    return RuleResult("P-05", "Fora de escopo", Severity.REQUIRED, bool(spec.out_of_scope))


def _p06_how_to_verify(spec: WorkItemSpec) -> RuleResult:
    return RuleResult("P-06", "Como verificar", Severity.REQUIRED, bool(spec.how_to_verify))


def _p07_open_questions(spec: WorkItemSpec | EpicSpec) -> RuleResult:
    n = len(spec.open_questions)
    detail = f"{n} pergunta(s) sem resposta" if n else ""
    return RuleResult("P-07", "Nenhuma pergunta em aberto", Severity.REQUIRED, n == 0, detail)


def _p08_vague_terms(text: str, cfg: ReadinessConfig) -> RuleResult:
    found: list[str] = []
    for sentence in _SENTENCE.findall(text):
        lowered = {w.lower() for w in _words(sentence)}
        has_number = any(ch.isdigit() for ch in sentence)
        for vague in cfg.vague_terms:
            vague_here = vague.term in lowered and not (vague.unless_number and has_number)
            if vague_here and vague.term not in found:
                found.append(vague.term)
    detail = f"termos: {', '.join(found)}" if found else ""
    return RuleResult("P-08", "Sem termos vagos", Severity.WARNING, not found, detail)


def _p09_length(body: str, cfg: ReadinessConfig) -> RuleResult:
    n = len(_words(body))
    ok = n <= cfg.max_body_words
    detail = "" if ok else f"{n} palavras (máximo {cfg.max_body_words})"
    label = f"Corpo com até {cfg.max_body_words} palavras"
    return RuleResult("P-09", label, Severity.WARNING, ok, detail)


def _p10_link_only(body: str, cfg: ReadinessConfig) -> RuleResult:
    lowered = body.lower()
    has_link = bool(_URL.search(body))
    defers = any(phrase in lowered for phrase in cfg.link_only_phrases)
    short = len(_words(_URL.sub("", body))) < cfg.min_body_words_with_link
    ok = not (has_link and (defers or short))
    detail = "" if ok else "o conteúdo depende de um link externo"
    return RuleResult("P-10", "Não depende só de link externo", Severity.WARNING, ok, detail)


def evaluate(spec: WorkItemSpec | EpicSpec, config: ReadinessConfig | None = None) -> Readiness:
    """Avalia as regras P-01 a P-10.

    Para épicos, P-03 vira critérios do épico + decomposição; P-04 e P-06 não se aplicam.
    """
    cfg = config or load_config()
    body = to_markdown(spec)
    text = f"{spec.title}\n{body}"
    if isinstance(spec, EpicSpec):
        structural = [_p01_title(spec, cfg), _p02_objective(spec), _p03_epic(spec)]
        structural += [_p05_out_of_scope(spec), _p07_open_questions(spec)]
    else:
        structural = [
            _p01_title(spec, cfg),
            _p02_objective(spec),
            _p03_criteria(spec, cfg),
            _p04_error_case(spec),
            _p05_out_of_scope(spec),
            _p06_how_to_verify(spec),
            _p07_open_questions(spec),
        ]
    warnings = [_p08_vague_terms(text, cfg), _p09_length(body, cfg), _p10_link_only(body, cfg)]
    return Readiness(cfg.version, tuple(structural + warnings))


def sensitive_terms_in(
    spec: WorkItemSpec | EpicSpec, config: ReadinessConfig | None = None
) -> list[str]:
    """Termos que sugerem segurança, dados pessoais, permissões ou pagamentos (RA-24)."""
    cfg = config or load_config()
    # "Fora de escopo" diz o que NÃO será feito: não conta como indício.
    in_scope = spec.model_copy(update={"out_of_scope": []})
    text = f"{spec.title}\n{to_markdown(in_scope)}".lower()
    return [term for term in cfg.sensitive_terms if term in text]


def labels_for(spec: WorkItemSpec | EpicSpec, readiness: Readiness) -> tuple[str, ...]:
    """Labels (RA-21, RA-24): `specflow` sempre; `agent-ready` se pronta e não `human-only`."""
    labels = [LABEL_SPECFLOW]
    if spec.human_only:
        labels.append(LABEL_HUMAN_ONLY)
    elif readiness.ready:
        labels.append(LABEL_AGENT_READY)
    return tuple(labels)
