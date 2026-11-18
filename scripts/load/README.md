# Teste de carga (F11-RT-08)

`chat.js` (k6) cria 50 contas no emulador de Auth e as põe para conversar com o LLM de eco por 2
minutos, cada uma com sua conversa nova a cada mensagem, perto do ritmo máximo que o rate limit deixa
(10 por minuto por usuário; pausa de 6 a 9 s, início espalhado). Como o modelo é fake, a duração medida é o overhead do backend. Metas:
erro < 1% e p95 < 500 ms.

```bash
DAILY_MESSAGE_QUOTA=100000 docker compose up -d emulators backend
docker run --rm -i --network host grafana/k6:0.57.0 run - < scripts/load/chat.js
# Saturação (sem o rate limit, 1 s entre mensagens, todos em fase): o teto de uma instância
DAILY_MESSAGE_QUOTA=100000 RATE_LIMIT_PER_MINUTE=1000 docker compose up -d emulators backend
docker run --rm -i --network host -e PAUSE=1 -e JITTER=0 grafana/k6:0.57.0 run - < scripts/load/chat.js
```

Os resultados entram na seção de evidências da F11. A instância local tem 1 processo uvicorn; o
Cloud Run escala por concorrência (40 por instância), então o número local é o pior caso.
