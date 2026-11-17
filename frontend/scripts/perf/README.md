# Medições da F08 (manuais, fora do CI)

Rodam contra a pilha local (emuladores + API com `LLM_PROVIDER=fake`). Resultados nas evidências de
`specs/008-interface-chat/spec.md`.

## F08-RT-03 — Lighthouse (mobile) em `/chat`

```bash
npm run build && npx vite preview --port 5173 --strictPort   # build de produção; CORS local aceita 5173
npm i --no-save lighthouse@12.8.2
node scripts/perf/lighthouse-chat.mjs /tmp/lh-profile /tmp/lh-report   # loga, cria uma conversa e mede
```

## F08-RT-06 — 5 mil tokens em streaming (≥ 50 fps)

```bash
node scripts/perf/sse-proxy.mjs                 # :8010 → API :8000; o POST de mensagens vira 5000 tokens
# MODE=table node scripts/perf/sse-proxy.mjs    # pior caso: uma tabela única, sem linha em branco
VITE_API_BASE_URL=http://localhost:8010 npx vite build --outDir /tmp/dist-perf
npx vite preview --outDir /tmp/dist-perf --port 5174 --strictPort
node scripts/perf/stream-fps.mjs                # fps, p95 do quadro e long tasks durante o turno
```
