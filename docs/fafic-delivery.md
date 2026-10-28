# Entrega FAFIC — 11/09/2026

## Escopo final solicitado

O painel público de administração foi reduzido a login por senha, ligar/desligar o chatbot e edição da mensagem de indisponibilidade. Não apresenta navegação SaaS, documentos, testes, ambientes, cotas, credenciais ou auditoria. As rotas antigas do painel redirecionam para a página única.

O visitante conversa normalmente no widget. O texto não recebe prefixo com nome de documento. As fontes são facultativas em “Ver fontes”, fechado por padrão. O aviso configurado aparece como mensagem de conversa quando o bot está desligado, quando a Groq atinge seu limite ou quando a geração falha. O contato escrito pelo administrador é texto; não há encaminhamento automático.

## Alterações internas

- Nova tabela `institution_config` vincula a instalação a um assistente existente e guarda apresentação e mensagem de indisponibilidade.
- Migration `20260910_0009` é aditiva: preserva as oito anteriores, cria a configuração e acrescenta fontes/confiança às mensagens. Não exclui registros.
- `scripts.setup_fafic` primeiro lista a estrutura. `--apply` reaproveita uma configuração inequívoca; múltiplos ambientes/assistentes exigem escolha explícita. Não há seleção arbitrária.
- A administração continua operando com o bot desligado. Sessões públicas existentes também respeitam o desligamento.
- Cotas comerciais antigas não bloqueiam o assistente vinculado à FAFIC. Permanecem nas estruturas legadas.
- Documentos entram como rascunho. A última versão publicada continua disponível enquanto a nova aguarda aprovação. Publicar a substituta retira a anterior das respostas. Retirar publicação não reativa versões antigas.
- Upload limitado a 20 MB e formatos PDF/DOCX/TXT/HTML; tratamento de arquivo corrompido e leitura de tabelas em DOCX. Falhas de sincronização guardam uma explicação.
- RAG mantém recuperação lexical, agora sem consulta extra por documento para carregar trechos. Não foi introduzido um provedor de embeddings. PostgreSQL foi preservado; a imagem Docker já inclui pgvector, mas a busca não usa vetores.
- Histórico e evidência possuem limites. Groq tem timeout e falhas configuradas não produzem resposta alternativa que esconda a indisponibilidade.
- Tokens públicos duram 15 minutos e são vinculados à origem, assistente e sessão. Token de retomada tem finalidade distinta e validade de 24 horas. O endpoint de conversa não aceita o token de retomada como autorização.
- Limites simples de requisições protegem a emissão pública e o envio de mensagens. São por processo; múltiplas instâncias exigem limite compartilhado no serviço de entrada.
- Login usa hash scrypt com sal individual, comparação de tempo constante, limite de tentativas, sessão assinada e cookie HttpOnly/SameSite=Strict. A senha local existente foi convertida para hash sem alterar a senha de acesso.

## Validações realizadas

- 36 testes de backend passaram, incluindo publicação, isolamento, origem, sessão, arquivos inválidos, desligamento e erro 429 da Groq com aviso personalizado.
- Teste de navegador passou em 320, 390, 768 e 1440 px: login incorreto/correto, persistência da mensagem, ligar/desligar, rotas antigas, widget, fontes recolhidas, retomada, falha de conexão e logout.
- Build de produção, lint e tipos da versão final do painel passaram com `npm run build`.
- PostgreSQL 18 separado: migrations 0001 a 0008 aplicadas; dados fictícios inseridos; migration 0009 aplicada; vinculação FAFIC reutilizou os registros; conteúdo anterior preservado.
- As migrations históricas não suportam execução completa em SQLite por alteração de constraints na revisão 0004. Elas foram preservadas e a validação de migrations foi realizada em PostgreSQL.
- Nenhuma chamada real à Groq foi necessária para esses testes. Limite e falhas de IA foram simulados.

## Preservação e execução

O Docker não estava acessível na sessão. O banco original não foi alterado nem resetado. Os bancos de validação foram separados. O backup original de 31/08/2026 foi preservado.

Para ativar no ambiente existente, iniciar Docker, executar a atualização normal dos serviços e revisar/vincular o assistente usando os comandos do README. A publicação da documentação continua disponível na API administrativa para manutenção técnica.

Não foram feitos commit, push ou deploy. `.env`, hash de senha, backups, bancos temporários e resultados de testes ficam fora do Git. `docs/first-commit-files.txt` registra o inventário candidato, sem preparar staging ou criar commit.

## Atualização — 16/09/2026

A pedido do usuário, a seção Documentos foi restaurada com upload, URL, revisão, publicação, retirada, exclusão confirmada e sincronização. O painel também abre o chat de teste em `/demo.html`. Foram preservados os controles simples e a autenticação.

O bloqueio do chat local foi diagnosticado: o backend permitia apenas a origem da porta 3000, enquanto o teste era aberto na porta 4173. As origens locais foram acrescentadas sem remover as anteriores, o backend foi reiniciado e o worker de importação iniciado. A Groq passou no diagnóstico real de geração. Os documentos existentes não foram excluídos nem publicados automaticamente.

Validação da atualização: 36 testes de backend, build/lint/tipos e teste de navegador de upload, revisão, publicação, retirada e confirmação de exclusão passaram. A busca local encontrou trechos nos documentos reais. O envio de conteúdo real à Groq para um teste adicional foi bloqueado pela revisão automática e não foi executado. O diagnóstico da Groq usou apenas uma solicitação sintética. O painel local foi atualizado e o banco existente preservado.
