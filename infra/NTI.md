# Proxy HTTPS da faculdade

Neste modelo, o NTI termina HTTPS para `chatbot.catolicapb.com.br` e encaminha todas as rotas, sem remover prefixos, para `http://10.0.0.248:8090`. Preserve o Host público. O Caddy interno distribui `/v1/*` e `/health` para a API e as demais rotas para o painel. Não há emissão de certificado neste Caddy.

Copie `Caddyfile.nti` e `compose.nti.yaml` para `infra/` na VPS. Na sessão root, use sempre os dois arquivos, inclusive após reconectar:

```bash
dc() {
  docker compose --env-file /opt/chatbot-platform/.env -p fafic -f /opt/chatbot-platform/infra/compose.production.yaml -f /opt/chatbot-platform/infra/compose.nti.yaml "$@"
}
dc config --quiet
dc run --rm --no-deps proxy caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
dc up -d --no-deps --force-recreate proxy
curl --max-time 10 -I http://10.0.0.248:8090/login
curl --max-time 10 http://10.0.0.248:8090/health
```

O Compose precisa ser 2.24.4 ou posterior para `!override`. Essa configuração substitui as portas públicas 80/443 do container por 8090 no IP privado. O NTI deve restringir a porta à sua rede/proxy conforme a política de infraestrutura.

Mantenha as URLs públicas HTTPS e `ADMIN_COOKIE_SECURE=true`. O endereço HTTP por IP permite conferir login/health, mas não deve ser usado para autenticar: o cookie seguro exige HTTPS. Teste login, logout, documentos, widget e redirecionamentos pelo domínio público depois do encaminhamento; caso algum redirecionamento exponha endereço interno ou HTTP, revise o Host encaminhado antes de abrir aos usuários.

Este arquivo substitui o fluxo de ativação do Caddy público no roteiro anterior. Não execute comandos Compose com apenas o arquivo de produção depois desta mudança, pois eles restaurariam a configuração antiga do proxy. Não use `down -v`.
