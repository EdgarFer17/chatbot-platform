# Arquitetura

## Decisão: monólito modular

A V1 será um monólito modular porque existe um único time de desenvolvimento, um fluxo principal de implantação e uma necessidade forte de consistência entre autenticação, tenant, conversa e conhecimento.

Isso não significa código misturado. Cada domínio possui fronteira, modelos, serviços, repositórios e rotas próprios. Comunicação entre módulos ocorre por interfaces internas, nunca por acesso improvisado às tabelas de outro módulo.

## Módulos previstos

```text
identity       operador, gestores e autenticação
tenancy        instituições e isolamento
environments   homologação e produção
assistants     configuração e comportamento
api_keys       credenciais e escopos
knowledge      fontes, documentos, versões e publicação
rag            chunking, embeddings, recuperação e geração
conversations  sessões, mensagens e contexto
usage          cotas, tokens e métricas
audit          eventos administrativos sanitizados
```

## Componentes de execução

- **FastAPI:** API pública e administrativa.
- **PostgreSQL + pgvector:** dados transacionais e busca vetorial na V1.
- **Worker independente:** processo separado da API que consome trabalhos persistidos no PostgreSQL e retoma filas interrompidas.
- **Provedor LLM:** adaptador substituível; Groq será a primeira implementação.
- **Admin Next.js:** será iniciado depois de estabilizar os contratos administrativos.

## Isolamento

Toda entidade pertencente a um cliente recebe `tenant_id`. Consultas de aplicação exigem contexto de tenant e testes automatizados comprovam que dados de tenants diferentes não podem ser combinados.

Os vetores também carregam `tenant_id`, `assistant_id`, `document_id`, versão, seção e posição. O filtro de tenant é obrigatório antes do ranqueamento.

## Núcleo implementado no marco 1

- `Tenant`: cliente contratante, como a FAFIC.
- `Environment`: separa homologação e produção dentro do cliente.
- `Assistant`: configuração pertencente a um ambiente.
- `ApiKey`: credencial revogável usada pela integração do cliente.

Ambientes, assistentes e chaves são consultados sempre junto do `tenant_id`.
Mesmo conhecendo o identificador de outro recurso, um cliente não atravessa essa
fronteira.

## API pública inicial

```text
POST /v1/sessions
POST /v1/sessions/{session_id}/messages
GET  /health
```

Na primeira entrega do contrato público já estão disponíveis a criação de
sessão, envio e consulta de mensagens e encerramento da sessão. A resposta atual
inclui fontes e confiança. A recuperação por trechos já preserva o contrato HTTP
e o adaptador Groq é ativado apenas quando sua chave e modelo estão configurados.

Perguntas de continuação utilizam somente as últimas seis mensagens da mesma
sessão, limitadas a oito mil caracteres. Esse contexto nunca é recuperado por
usuário externo nem compartilhado entre sessões, ambientes ou instituições.

## Evolução para serviços separados

Somente extrairemos um módulo quando houver evidência operacional, como necessidade de escalar ingestão independentemente, filas longas ou equipes distintas. As primeiras candidatas são ingestão documental e processamento assíncrono.
