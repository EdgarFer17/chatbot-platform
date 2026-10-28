# Publicar em chatbot.catolicapb.com.br

Roteiro para VPS nova, Debian 12/13 ou Ubuntu 22.04/24.04/26.04, com acesso SSH administrativo. Execute um bloco por vez e pare se houver erro. Não execute os passos de instalação em servidor que já tenha serviços sem revisar conflitos primeiro. Nada deste roteiro foi executado na VPS pelo assistente.

Use duas janelas: **PowerShell local** no Windows e **SSH da VPS**. `USUARIO` e `IP_DA_VPS` devem ser substituídos pelo acesso que você já utiliza. Se SSH usa outra porta, acrescente `-p PORTA` no ssh e `-P PORTA` no scp.

## 1. Identificar o servidor — SSH da VPS

```bash
cat /etc/os-release
whoami
uname -m
free -h
df -h /
ss -ltn
command -v docker
```

Se já houver Docker, sites ou portas 80/443 ocupadas, revise antes de continuar. O código `command -v docker` sem saída só indica que Docker não está instalado. Se o usuário for `root`, os comandos abaixo funcionam sem `sudo`; nos demais casos, use `sudo -i` uma vez para entrar como administrador.

## 2. DNS e portas

No DNS de `catolicapb.com.br`, crie/confira registro A de nome `chatbot` apontando para o IP público da VPS. Não altere o registro do site principal. Se houver AAAA, ele deve apontar para IPv6 funcional desta VPS. Durante a instalação, use DNS direto, sem proxy intermediário.

No firewall do provedor, permita TCP 80/443 e mantenha a porta SSH atual permitida. Não é necessário expor 3000, 8010 ou 5432. Não ative nem redefina o firewall local às cegas, pois isso pode cortar o SSH.

No PowerShell local:

```powershell
Resolve-DnsName chatbot.catolicapb.com.br -Type A
```

O endereço retornado deve coincidir com o IP público da VPS.

## 3. Instalar Docker — SSH como root

Para uma VPS nova sem Docker. O bloco seleciona o repositório oficial da distribuição. Não desinstala pacotes existentes automaticamente; se houver conflito, pare e revise.

```bash
bash <<'INSTALL'
set -euo pipefail
. /etc/os-release
case "$ID:$VERSION_ID" in
  debian:12|debian:13|ubuntu:22.04|ubuntu:24.04|ubuntu:26.04) ;;
  *) echo "Sistema fora deste roteiro: $ID $VERSION_ID"; exit 1 ;;
esac
apt-get update
apt-get install -y ca-certificates curl python3 nano dnsutils
install -m 0755 -d /etc/apt/keyrings
curl -fsSL "https://download.docker.com/linux/$ID/gpg" -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
cat > /etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/$ID
Suites: ${UBUNTU_CODENAME:-$VERSION_CODENAME}
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable --now docker
docker version
docker compose version
INSTALL
```

Fontes: instalação oficial [Debian](https://docs.docker.com/engine/install/debian/) e [Ubuntu](https://docs.docker.com/engine/install/ubuntu/).

## 4. Empacotar código — PowerShell local

Use o projeto atualizado por esta tarefa. O pacote não inclui `.env`, banco ou dependências locais. Não use `scp -r` da pasta inteira.

```powershell
cd C:\Users\Edgar\Trabalho\Projetos\chatbot-platform
New-Item -ItemType Directory -Force backups | Out-Null
tar --exclude=node_modules --exclude=.next --exclude=.next-qa --exclude=.venv --exclude=__pycache__ --exclude=.pytest_cache --exclude=.env --exclude='.env.*' --exclude='*.log' --exclude='*.dump' --exclude='*.db' --exclude='*.sqlite*' --exclude='*.tsbuildinfo' -czf backups/chatbot-release.tar.gz admin backend widget infra docs README.md
if ($LASTEXITCODE -ne 0) { throw 'Falha ao empacotar o projeto' }
scp backups/chatbot-release.tar.gz USUARIO@IP_DA_VPS:chatbot-release.tar.gz
```

## 5. Backup dos documentos — PowerShell local

Abra Docker Desktop. Não faça novas alterações locais depois do backup até concluir a transferência. O backup inclui a base completa, inclusive conversas e documentos; transfira somente para a VPS autorizada da faculdade.

```powershell
cd C:\Users\Edgar\Trabalho\Projetos\chatbot-platform
docker compose up -d database
docker compose exec -T database pg_isready -U chatbot -d chatbot_platform
```

Espere aparecer `accepting connections`, então:

```powershell
docker compose exec -T database pg_dump -U chatbot -d chatbot_platform -Fc -f /tmp/fafic-vps.dump
if ($LASTEXITCODE -ne 0) { throw 'Backup falhou; não continue' }
docker compose cp database:/tmp/fafic-vps.dump backups/fafic-vps.dump
if ($LASTEXITCODE -ne 0) { throw 'Cópia do backup falhou; não continue' }
Get-Item backups/fafic-vps.dump | Select-Object Name,Length
docker compose exec -T database psql -U chatbot -d chatbot_platform -c "SELECT status, count(*) FROM knowledge_documents GROUP BY status;"
scp backups/fafic-vps.dump USUARIO@IP_DA_VPS:fafic-vps.dump
```

Guarde as quantidades para comparar na VPS. Se o Docker local não iniciar, resolva esse bloqueio antes de tentar preservar os dados: o pacote de código não contém os documentos.

## 6. Extrair — SSH da VPS

Antes de virar root, anote `pwd` para localizar a pasta em que o scp colocou os arquivos. Nos comandos abaixo substitua `/home/USUARIO` por ela; se o acesso foi root, use `/root`.

Como root, crie a pasta apenas se ainda não existir:

```bash
mkdir -m 700 /opt/chatbot-platform
tar -xzf /home/USUARIO/chatbot-release.tar.gz -C /opt/chatbot-platform
install -m 600 /home/USUARIO/fafic-vps.dump /opt/chatbot-platform/fafic-vps.dump
cd /opt/chatbot-platform
```

Se `mkdir` disser que a pasta já existe, confira seu conteúdo antes de extrair por cima.

## 7. Configurar senha e Groq — SSH como root

```bash
cd /opt/chatbot-platform
python3 infra/configure-production.py
```

O assistente de configuração pede uma senha nova de pelo menos 12 caracteres, confirmação e chave Groq (digitação oculta). Depois pergunta as origens HTTPS do site: informe os endereços reais, separados por vírgula, ou Enter para autorizar inicialmente só `https://chatbot.catolicapb.com.br`. Isso permite testar antes da instalação no site principal.

Ele gera `.env` com segredos independentes e a senha em hash; não substitui arquivo existente. Não reutilize a senha de teste `12345678`. Não cole a chave ou o conteúdo do `.env` na conversa.

Na mesma sessão SSH, crie um atalho para os comandos:

```bash
dc() { docker compose --env-file /opt/chatbot-platform/.env -p fafic -f /opt/chatbot-platform/infra/compose.production.yaml "$@"; }
dc config --quiet
```

Sem saída e sem erro significa configuração válida. Recrie a função `dc` sempre que abrir uma nova sessão SSH.

## 8. Restaurar banco — SSH como root

Inicie **somente** o banco:

```bash
dc up -d --wait database
dc exec -T database psql -U chatbot -d chatbot_platform -Atc "SELECT count(*) FROM pg_tables WHERE schemaname='public';"
```

O resultado precisa ser **0**. Se não for, pare: já há estrutura/dados e não devemos restaurar por cima.

Com resultado zero, execute:

```bash
dc cp /opt/chatbot-platform/fafic-vps.dump database:/tmp/fafic-vps.dump
dc exec -T database pg_restore --exit-on-error --single-transaction --no-owner --no-privileges -U chatbot -d chatbot_platform /tmp/fafic-vps.dump
dc exec -T database psql -U chatbot -d chatbot_platform -c "SELECT status, count(*) FROM knowledge_documents GROUP BY status;"
```

Se pg_restore falhar, não siga adiante. Compare as quantidades com o computador local. O restore não usa `--clean` nem exclui o banco. Os novos segredos invalidam sessões temporárias antigas, mas preservam documentos/conversas armazenados. Integrações legadas que usavam a chave administrativa precisam da nova configuração.

## 9. Construir e iniciar — SSH como root

```bash
dc build backend worker admin
dc up -d --wait backend worker admin
dc exec -T backend python -m scripts.setup_fafic
dc exec -T backend python -m scripts.setup_fafic --apply
curl --fail http://127.0.0.1:8010/health
```

`setup_fafic --apply` reaproveita a vinculação restaurada. Se houver ambiguidade no inventário, pare e selecione o assistente correto. As migrações são aplicadas pelo backend ao iniciar.

Valide o proxy antes de publicá-lo:

```bash
dc run --rm --no-deps proxy caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
dc up -d proxy
dc ps
dc logs --tail 80 proxy
```

O certificado HTTPS depende do DNS correto e das portas 80/443 acessíveis. [Documentação Caddy](https://caddyserver.com/docs/automatic-https).

## 10. Verificar

```bash
curl --fail https://chatbot.catolicapb.com.br/health
curl -I https://chatbot.catolicapb.com.br/login
curl -I https://chatbot.catolicapb.com.br/chatbot-widget.js
```

No navegador:

- Painel: https://chatbot.catolicapb.com.br
- Documentos: https://chatbot.catolicapb.com.br/documentos
- Chat de teste: https://chatbot.catolicapb.com.br/demo.html

Entre com a senha nova, confira os documentos publicados, configure o aviso de indisponibilidade e ligue o bot. Ao enviar perguntas sobre os documentos, os trechos relevantes são enviados à Groq para geração. Não é necessário enviar consultas para testar apenas health/login.

## 11. Instalar no site da faculdade

Autorize a origem exata do site em `ALLOWED_ORIGINS` no `.env`, mantendo também o domínio do chatbot. Depois:

```bash
dc up -d --no-deps --force-recreate backend
```

Entregue ao responsável pelo frontend este trecho, para inserir uma vez antes de `</body>`:

```html
<script type="module" src="https://chatbot.catolicapb.com.br/chatbot-widget.js"></script>
<chatbot-platform api-url="https://chatbot.catolicapb.com.br" accent-color="#173b73"></chatbot-platform>
```

Confira celular, navegação e políticas CSP do site conforme [guia de integração](instalacao-site.md).

## 12. Operação

Ver problemas:

```bash
dc ps
dc logs --tail 100 backend worker admin proxy
```

Backup da VPS:

```bash
mkdir -p /opt/chatbot-platform/backups
chmod 700 /opt/chatbot-platform/backups
umask 077
dc exec -T database pg_dump -U chatbot -d chatbot_platform -Fc > "/opt/chatbot-platform/backups/fafic-$(date +%Y%m%d-%H%M%S).dump"
```

Confira que terminou sem erro; mantenha cópia fora da VPS e uma cópia protegida do `.env`. Configure rotina de backup e teste restauração em banco separado. Não use `dc down -v`, pois exclui os volumes. Os containers reiniciam com o servidor, exceto se tiverem sido parados manualmente. O computador local pode ficar desligado.
