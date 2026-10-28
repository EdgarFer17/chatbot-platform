# Assistente institucional da FAFIC

O visitante abre o botão de chat no site e conversa normalmente. O backend consulta somente documentos publicados e usa a Groq para gerar a resposta. As fontes ficam em uma opção discreta, fechada por padrão; o texto não começa com o título do documento.

O painel possui:
- acesso por senha;
- ligar e desligar o chatbot;
- editar a mensagem de indisponibilidade;
- enviar documentos ou URLs, revisar, publicar e sincronizar a base de conhecimento.

Quando o bot está desligado, a Groq atinge um limite ou ocorre falha de geração, o visitante recebe o aviso configurado. Um telefone ou contato pode ser escrito nesse aviso; não existe integração automática com atendimento humano.

## Estrutura preservada

- `admin/`: painel Next.js e distribuição do widget.
- `backend/`: FastAPI, RAG, importação, autenticação e processamento de fontes.
- `widget/`: componente incorporável e demonstração local.
- `backend/migrations/`: histórico existente e atualização aditiva da configuração FAFIC.
- `backups/`: backup local preservado e ignorado pelo Git.

O cadastro e a publicação estão na seção Documentos do painel (`/documentos`). O link Testar chat abre `/demo.html`, sem precisar iniciar outro servidor. A estrutura interna de instituições e ambientes permanece preservada.

## Executar localmente com Docker

1. Prepare `.env` a partir de `.env.example`, preservando o arquivo existente. Configure `GROQ_API_KEY` somente nesse arquivo ou no ambiente do backend.
2. Configure a senha segura. A senha local anterior foi convertida em hash sem alterar seu valor. Para uma nova instalação:

```powershell
cd admin
node scripts/hash-password.mjs
cd ..
```

Copie a linha `ADMIN_PASSWORD_HASH=...` produzida para `.env`. O comando não exibe a senha digitada. `ADMIN_SESSION_SECRET` deve ser um segredo aleatório independente.

3. Inicie os serviços locais:

```powershell
docker compose up --build -d
```

4. Consulte a estrutura existente antes de vincular a FAFIC:

```powershell
docker compose exec backend python -m scripts.setup_fafic
```

5. Se houver uma única instituição FAFIC, um ambiente e um assistente, conclua:

```powershell
docker compose exec backend python -m scripts.setup_fafic --apply
```

Em uma base vazia, esse comando cria a estrutura FAFIC com o bot inicialmente desligado. Em uma base existente, reaproveita os registros. Se houver vários ambientes ou assistentes, não escolhe por conta própria: revise o inventário e execute com `--assistant-id UUID_ESCOLHIDO`. O comando é idempotente e não exclui dados.

Abra o painel em http://localhost:3005 e entre com sua senha. A API local fica em http://localhost:8010. Publicar no servidor ou no site oficial é uma etapa separada.

## Instalar o widget

Veja [widget/README.md](widget/README.md). O arquivo é servido pelo painel em `/chatbot-widget.js`. O domínio do site precisa estar na lista `ALLOWED_ORIGINS` do backend.

## Validação

```powershell
backend/.venv/Scripts/python.exe -m pytest backend/tests -q
cd admin
npm ci
npm run build
```

O build inclui lint e verificação de tipos. O `prebuild` copia o widget original para `admin/public` para manter ambos iguais. As chaves reais da Groq nunca são utilizadas pelos testes unitários.

[Detalhes da implementação e validação](docs/fafic-delivery.md).

## Site da faculdade e VPS Ubuntu

- [Passo a passo completo para chatbot.catolicapb.com.br (Debian/Ubuntu)](docs/vps-catolica.md).

- [Trecho e instruções para o responsável pelo site](docs/instalacao-site.md).
- [Instalação e operação na VPS Ubuntu](infra/README.md).
- Paleta atual: azul `#173b73` e dourado `#d9b45b`.
