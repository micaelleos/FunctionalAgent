# Espaço modelo do Confluence (um por projeto Jira)

> Parte da [metodologia SpecFlow](README.md). É o formato que a F20 cria e a F19 lê.

## 1. Árvore

```
<Projeto> — Documentação                (espaço; chave = chave do projeto Jira quando possível)
├── Início                               visão, público, links para o Jira e o app
├── Constituição                         regras inegociáveis do projeto, versionadas
├── Glossário                            termos do domínio
├── Regras de negócio                    RN-01, RN-02… (uma tabela; detalhe em filhas, se preciso)
├── Arquitetura                          visão técnica, integrações, onde fica cada coisa
├── Decisões (ADR)
│   ├── ADR-001 — <título>
│   └── ADR-002 — <título>
├── Roadmap                              features, status, dependências, chaves do Jira
├── Features
│   ├── <FEAT-01> — <nome>               uma página por épico (o "spec.md" do projeto)
│   └── <FEAT-02> — <nome>
└── Registro de mudanças                 uma linha por escrita do SpecFlow
```

## 2. Rótulos (leitura por máquina)

| Rótulo | Onde | Para quê |
|---|---|---|
| `specflow` | todas as páginas do modelo | o SpecFlow sabe que a página segue o modelo |
| `specflow-projeto-<chave>` | página **Início** | vínculo automático quando a chave do espaço difere da do projeto |
| `specflow-tipo-<tipo>` | cada página | o agente acha a página certa sem depender do título. Tipos: `inicio`, `constituicao`, `glossario`, `regras`, `arquitetura`, `adr`, `roadmap`, `feature`, `registro` |

Títulos podem ser renomeados pelo time. O SpecFlow acha as páginas pelos rótulos e, na falta deles,
pelo título do modelo.

## 3. Convenções

- **IDs estáveis:**
  - regras `RN-nn`;
  - decisões `ADR-nnn`;
  - features `FEAT-nn`;
  - critérios de aceite das stories `CA-nn`.

  Um ID nunca é reutilizado. Regra revogada fica riscada com a data.
- **Versão da Constituição:** SemVer na primeira linha. MAJOR remove ou redefine uma regra, MINOR
  acrescenta, PATCH só muda a redação.
- **Ligação com o Jira:**
  - a página da feature traz a chave do épico (`SCRUM-10`);
  - o Roadmap traz a chave de cada épico;
  - os issues trazem a página em "Referências".
- **Idioma:** o do time. O SpecFlow escreve as specs em pt-BR hoje (doc 10).
- **Tamanho:** páginas do modelo cabem em ~8 mil caracteres, o limite que o agente lê (F19-RT-04).
  Detalhe longo vai para páginas filhas.

## 4. Como o agente usa cada página

| Página | Fase 1 (Descobrir) | Fase 5 (Verificar) | Fase 7 (Convergir) |
|---|---|---|---|
| Constituição | sempre lida | spec que fere uma regra gera aviso | propõe emenda se o PO decidiu mudar uma regra |
| Glossário | sempre lida | termo novo ou usado com outro sentido gera aviso | propõe o termo novo |
| Regras de negócio | sempre lida | spec que contradiz `RN-nn` gera aviso; regras aplicáveis entram em "Restrições" | propõe regra nova/alterada |
| Decisões (ADR) | títulos + status; lê as relacionadas | spec que contraria ADR aceita gera aviso | propõe ADR nova |
| Arquitetura | lida se o pedido é técnico | — | aponta se ficou desatualizada |
| Features | busca a feature relacionada | evita duplicar escopo | atualiza a página com as stories criadas |
| Roadmap | lido para dependências | — | atualiza status e chaves |
| Registro de mudanças | — | — | uma linha por escrita confirmada |
