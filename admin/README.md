# Controle do chatbot FAFIC

Painel com login por senha, controle do chatbot e seção Documentos para upload, importação por URL, revisão, publicação, retirada e sincronização. O link Testar chat abre a demonstração local em `/demo.html`. Não há carteira de clientes, cadastro de ambientes, consumo ou auditoria na interface.

Para executar fora do Docker, copie `.env.example` para `.env.local` e preencha a URL interna da API, a credencial administrativa, `ADMIN_PASSWORD_HASH` e `ADMIN_SESSION_SECRET`. Gere o hash com `node scripts/hash-password.mjs`. Use a mesma credencial administrativa configurada no backend.

```powershell
npm ci
npm run dev
```

Validação: `npm run build` inclui compilação, lint e tipos.

A senha é verificada com scrypt, sal individual e comparação de tempo constante. A sessão é assinada, dura oito horas e usa cookie HttpOnly/SameSite=Strict. Em HTTPS, configure `ADMIN_COOKIE_SECURE=true`. A chave administrativa é usada somente pelo servidor Next.js. O navegador só pode chamar os controles institucionais permitidos.

`node scripts/migrate-password.mjs` converte uma senha existente em `../.env` para hash sem exibi-la e sem alterar as demais configurações. Um caminho alternativo pode ser passado como argumento. O hash não deve ser versionado.
