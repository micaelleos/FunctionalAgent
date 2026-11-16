"""Specs de exemplo para os testes do `AgentReadySpec` (história do Pix do doc 10 §4.2)."""

from typing import Any

from app.agent.spec.schema import EpicSpec, WorkItemSpec


def pix_story_data(**overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "type": "story",
        "title": "Permitir pagamento com Pix no checkout da loja",
        "objective": (
            "Como cliente, quero pagar meu pedido com Pix, para concluir a compra sem cartão."
        ),
        "context": [
            "O checkout aceita só cartão (`PaymentMethod.CARD`).",
            'O provedor de pagamentos já expõe `POST /pix/charges` (ver "Restrições e contratos").',
        ],
        "acceptance_criteria": [
            {
                "id": "CA-01",
                "kind": "principal",
                "title": "Gerar cobrança Pix",
                "given": ["estou no checkout com um pedido de R$ 120,00"],
                "when": ['escolho "Pix"'],
                "then": ['vejo o QR Code e o texto "Pague em até 30 minutos"'],
            },
            {
                "id": "CA-02",
                "kind": "erro",
                "title": "Provedor indisponível",
                "given": ["o provedor responde 503"],
                "when": ['escolho "Pix"'],
                "then": [
                    'vejo "Pix indisponível no momento. Tente cartão ou aguarde alguns minutos."',
                    'o pedido continua com status "aguardando pagamento"',
                ],
            },
        ],
        "out_of_scope": ["Estorno de Pix.", "Pix parcelado."],
        "constraints": ["Expiração da cobrança: 30 minutos."],
        "how_to_verify": [
            "Testes de unidade para a criação da cobrança e o tratamento do 503.",
            "Teste E2E do CA-01 com o provedor simulado.",
            "Pronto quando: CA-01 e CA-02 passam; nenhuma mudança fora do checkout.",
        ],
    }
    data.update(overrides)
    return data


def pix_story(**overrides: Any) -> WorkItemSpec:
    return WorkItemSpec.model_validate(pix_story_data(**overrides))


PIX_MARKDOWN = """\
## Objetivo
Como cliente, quero pagar meu pedido com Pix, para concluir a compra sem cartão.

## Contexto
- O checkout aceita só cartão (`PaymentMethod.CARD`).
- O provedor de pagamentos já expõe `POST /pix/charges` (ver "Restrições e contratos").

## Critérios de aceite
**CA-01 (principal) Gerar cobrança Pix**
Dado estou no checkout com um pedido de R$ 120,00
Quando escolho "Pix"
Então vejo o QR Code e o texto "Pague em até 30 minutos"

**CA-02 (erro) Provedor indisponível**
Dado o provedor responde 503
Quando escolho "Pix"
Então vejo "Pix indisponível no momento. Tente cartão ou aguarde alguns minutos."
E o pedido continua com status "aguardando pagamento"

## Fora de escopo
- Estorno de Pix.
- Pix parcelado.

## Restrições e contratos
- Expiração da cobrança: 30 minutos.

## Como verificar
- Testes de unidade para a criação da cobrança e o tratamento do 503.
- Teste E2E do CA-01 com o provedor simulado.
- Pronto quando: CA-01 e CA-02 passam; nenhuma mudança fora do checkout.

## Perguntas em aberto
(nenhuma)
"""


def payments_epic(**overrides: Any) -> EpicSpec:
    data: dict[str, Any] = {
        "type": "epic",
        "title": "Oferecer novos meios de pagamento no checkout",
        "objective": "Aumentar a conversão do checkout com Pix e boleto.",
        "problem": "18% dos carrinhos são abandonados na etapa de pagamento por falta de opções.",
        "benefits": ["Conversão do checkout de 62% para 70%."],
        "scope": ["Pix", "Boleto"],
        "out_of_scope": ["Criptomoedas."],
        "acceptance_criteria": ["Pix e boleto disponíveis para 100% dos pedidos."],
        "decomposition": [
            {"title": "Permitir pagamento com Pix no checkout", "key": "PAG-121"},
            {"title": "Permitir pagamento com boleto", "depends_on": ["PAG-121"]},
        ],
    }
    data.update(overrides)
    return EpicSpec.model_validate(data)
