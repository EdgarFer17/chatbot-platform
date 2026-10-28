# Roteiro de desenvolvimento

## Marco 0 — Fundação

- [x] Estrutura do repositório.
- [x] Aplicação FastAPI executável.
- [x] Configuração segura.
- [x] Testes e Docker locais.
- [x] Documentação arquitetural.

## Marco 1 — Multi-tenancy

- [x] PostgreSQL, Alembic e pgvector.
- [x] Tenant, ambiente e assistente.
- [x] Contexto obrigatório de tenant.
- [x] Testes de isolamento negativos.

## Marco 2 — Credenciais e administração

- [ ] Autenticação e perfis do operador da plataforma.
- [x] Chaves de API armazenadas com hash e revogação.
- [x] Ativar e suspender ambientes.
- [ ] Rotação, escopos avançados e auditoria sanitizada.

## Marco 3 — Conhecimento

- [x] Fontes e documentos versionados.
- [x] Importação segura de site, URL, PDF, DOCX, TXT e HTML.
- [x] Rascunho, revisão e publicação manual.
- [x] Detecção de conteúdo inalterado por checksum.
- [x] Processamento assíncrono em worker e progresso persistido.
- [x] Descoberta por sitemap e rastreamento interno controlado.
- [x] Chunking e recuperação filtrada por tenant/assistente.
- [x] Citações por documento e confiança no contrato público.
- [ ] Agendamento, tentativas por arquivo, embeddings semânticos e reindexação vetorial.
- [ ] Citações por página e OCR.

## Marco 4 — Conversação

- [x] Sessões e mensagens públicas autenticadas por chave.
- [x] Contexto limitado e memória controlada por sessão.
- [x] Recuperação por trechos, geração opcional e fontes citadas.
- [x] Confiança e recusa segura quando não há evidência.
- [x] Cotas, consumo, métricas e limites por cliente.

## Marco 5 — Piloto FAFIC

- [ ] Dados e documentação de homologação.
- [x] Contrato OpenAPI candidato estável (`1.0.0-rc.1`).
- [x] Coleção de testes para a equipe integradora.
- [x] Teste de carga leve em homologação: 20/20, p95 1,225 s, sem 5xx.
- [x] Revisão automatizada inicial de segurança HTTP.
- Implantação isolada na VPS autorizada.

## Marco 6 — Painel e widget

- [x] Painel administrativo inicial do operador.
- Painel limitado para instituições.
- [x] Token temporário do widget vinculado à origem e ao assistente.
- [ ] Widget incorporável validado visualmente em homologação.
