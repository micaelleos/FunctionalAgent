# ADR-001 — Firestore como banco de dados por usuário

- **Status:** Proposto · **Data:** 2026-11-13

## Contexto

O app atual não persiste nada (`st.session_state`). Com usuários autenticados precisamos guardar, por usuário:
perfil, conexões Jira (com token cifrado), conversas e mensagens, ações propostas aguardando confirmação,
histórico de issues exportados e consumo diário (cotas). Padrões de acesso:

- Quase sempre "do usuário X, liste Y ordenado por data, paginado".
- Escritas pequenas e frequentes (mensagens), leituras de histórico da conversa a cada turno.
- Sem relatórios analíticos, sem joins entre usuários.
- Volume inicial baixo (dezenas de usuários), com picos imprevisíveis.

## Opções

| Critério | **Firestore (nativo)** | Cloud SQL (PostgreSQL) | Realtime Database |
|---|---|---|---|
| Custo em repouso | ~0 (nível gratuito) | ≥ ~US$ 10–30/mês (instância sempre ligada) | ~0 |
| Operação | Nenhuma | Patches, conexões, pool, backups | Nenhuma |
| Escala | Automática | Vertical / réplicas | Automática, limites por instância |
| Modelo | Documentos/subcoleções — encaixa em conversa/mensagens | Relacional — ótimo para relatórios | Árvore JSON — consultas pobres |
| Integração Firebase Auth | Nativa | Manual | Nativa |
| Consultas | Índices compostos, sem joins | SQL completo | Muito limitadas |
| Transações | Sim | Sim | Limitadas |
| TTL, PITR, backups | Sim | Sim | Backups apenas |

## Decisão

Usar **Firestore em modo nativo**, região `us-central1` (decisão do PO em 2026-11-14; o plano original previa `southamerica-east1`), com:
- Hierarquia `users/{uid}/...` para isolamento por caminho.
- Acesso **somente pelo backend** (Admin SDK + IAM); regras do cliente negam tudo.
- Mensagens em subcoleção; TTL em `pending_actions`; PITR e backup diário em prd.

## Consequências

- ✅ Custo próximo de zero no início; zero operação; transações para idempotência das ações.
- ✅ Isolamento por usuário é estrutural.
- ⚠️ Relatórios agregados (ex.: uso por todos os usuários) exigem export para BigQuery (extensão oficial) — aceitável quando necessário.
- ⚠️ Repositórios precisam encapsular o SDK para permitir testes com emulador e eventual troca.
- 🔁 Revisitar se surgir necessidade de buscas textuais ricas no histórico (avaliar Vertex AI Search/pgvector)
  ou de colaboração multiusuário em workspaces (modelo `workspaces/{id}` com membros).
