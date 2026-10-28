# Instalar na VPS Ubuntu

Para a instalação com **um único domínio `chatbot.catolicapb.com.br`**, use o [roteiro Debian/Ubuntu com todos os comandos](../docs/vps-catolica.md). O roteiro abaixo é o modelo anterior com dois subdomínios. Não misture os dois durante a instalação.

Modelo para Docker Engine e Compose com Caddy/HTTPS. Ainda não foi implantado nem validado em VPS real. Os domínios são exemplos. Confira serviços existentes, portas e backups antes de instalar.

## 1. Acessos e domínios

Solicite IP público, versão do Ubuntu, usuário SSH com sudo e acesso por chave SSH. Não compartilhe chaves privadas na conversa. Peça dois subdomínios, por exemplo `painel.exemplo.edu.br` e `api-chat.exemplo.edu.br`, com registros A para o IP da VPS. Use AAAA somente se IPv6 estiver funcionando.

Instale Docker Engine e o plugin Compose pelo [guia oficial do Ubuntu](https://docs.docker.com/engine/install/ubuntu/). Libere 80/443 no firewall da VPS/provedor e preserve seu acesso SSH. O banco não publica porta e os serviços internos estão em loopback, pois [Docker tem regras próprias de rede](https://docs.docker.com/engine/network/port-publishing/).

## 2. Código e configuração

Copie o projeto para `/opt/chatbot-platform` por Git privado ou SFTP, incluindo `admin/public`, backend, widget e infra. Não copie `.env` de testes, `.git`, `node_modules`, `.next`, `.venv` ou backups no pacote. Copiar o código não transfere os documentos do banco.

Na VPS, apenas em uma instalação nova sem `.env` existente:

```bash
cd /opt/chatbot-platform
cp infra/production.env.example .env
chmod 600 .env
nano .env
```

Configure domínios, URLs HTTPS, origens permitidas e chave Groq. Execute `openssl rand -hex 32` quatro vezes para gerar valores independentes de `POSTGRES_PASSWORD`, `JWT_SECRET_KEY`, `ADMIN_MASTER_KEY` e `ADMIN_SESSION_SECRET`. Use senha hexadecimal para o banco, pois ela é interpolada na URL de conexão.

No computador local, gere uma senha de produção (não use `12345678`):

```powershell
cd admin
node scripts/hash-password.mjs
```

Copie somente o hash produzido para `ADMIN_PASSWORD_HASH` no `.env` da VPS.

## 3. Banco existente ou instalação nova

Para levar os documentos/conversas atuais, faça um backup novo e planeje a restauração no banco vazio da VPS **antes de iniciar backend/worker**. Não restaure sobre dados existentes. Confirme o destino, preserve uma cópia local e compare documentos/publicações após a transferência. O backup antigo pode não conter alterações recentes. Revise também credenciais vinculadas antes de rotacionar segredos. Essa migração deve ser feita separadamente dos passos de instalação nova abaixo.

## 4. Iniciar uma instalação nova

Use sempre o arquivo de produção e o mesmo nome de projeto:

```bash
cd /opt/chatbot-platform
docker compose --env-file .env -p fafic -f infra/compose.production.yaml config --quiet
docker compose --env-file .env -p fafic -f infra/compose.production.yaml up --build -d
docker compose --env-file .env -p fafic -f infra/compose.production.yaml ps
docker compose --env-file .env -p fafic -f infra/compose.production.yaml exec backend python -m scripts.setup_fafic
```

Após conferir o inventário (base nova ou uma única FAFIC/ambiente/assistente):

```bash
docker compose --env-file .env -p fafic -f infra/compose.production.yaml exec backend python -m scripts.setup_fafic --apply
```

Se houver múltiplos assistentes, escolha o UUID correto com `--assistant-id`. O backend aplica migrações ao iniciar. O Caddy configura [HTTPS automaticamente](https://caddyserver.com/docs/quick-starts/https) quando DNS e portas estão corretos.

Entre no domínio do painel, envie/revise/publique documentos e ligue o bot. Instale o trecho do [guia para o frontend](../docs/instalacao-site.md). `/demo.html` detecta localhost para testes locais e usa o próprio domínio na instalação com domínio único. Para o modelo com dois subdomínios, valide no site real usando a URL da API no widget.

## 5. Operação

Ver logs:

```bash
docker compose --env-file .env -p fafic -f infra/compose.production.yaml logs --tail 100 backend worker admin proxy
```

Backup no Ubuntu (contém dados privados):

```bash
mkdir -p backups
chmod 700 backups
umask 077
docker compose --env-file .env -p fafic -f infra/compose.production.yaml exec -T database pg_dump -U chatbot -d chatbot_platform -Fc > "backups/fafic-$(date +%Y%m%d-%H%M%S).dump"
```

Mantenha cópia protegida fora da VPS e teste a restauração em banco separado. Faça backup antes de atualizar o código; depois repita `up --build -d`. Não use `down -v`, pois exclui os volumes do banco. Mudar `POSTGRES_PASSWORD` no `.env` não altera automaticamente a senha de um banco já criado.

Os containers usam `unless-stopped`. Configure monitoramento e rotina de backups na operação da faculdade. Antes da abertura pública, revise dependências e limites da Groq. O limite de requisições atual é local ao processo: mantenha uma instância do backend ou revise esse mecanismo antes de escalar.
