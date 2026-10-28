# Entrega ao responsável pelo site

O chatbot roda na VPS. O site carrega o widget uma vez no layout global, antes de `</body>`. Após publicar a VPS, substitua os domínios de exemplo pelos endereços HTTPS reais:

```html
<script type="module" src="https://painel.exemplo.edu.br/chatbot-widget.js"></script>
<chatbot-platform api-url="https://api-chat.exemplo.edu.br" accent-color="#173b73"></chatbot-platform>
```

O botão aparece no canto inferior direito, com azul e detalhes dourados. Em React/Next.js, carregue o script no navegador e monte o componente uma vez no layout; adapte a declaração JSX do elemento personalizado ao projeto. Em WordPress, use o mecanismo de código personalizado do rodapé global.

No backend, inclua em `ALLOWED_ORIGINS` as origens exatas do site (protocolo e domínio, sem caminho/barra final), incluindo `www` e homologação se usados. Recrie o backend após alterar a configuração.

Não envie `.env`, senha do painel, chave Groq ou `ADMIN_MASTER_KEY` ao frontend. Os tokens temporários são obtidos automaticamente.

Se houver CSP, permita o domínio do painel em `script-src` e o da API em `connect-src`. O componente injeta estilos inline no Shadow DOM: uma política que os bloqueie requer adaptação do widget/política antes da instalação. Não substitua indiscriminadamente a política existente.

Teste no endereço real: abrir/fechar, enviar pergunta, navegar, usar no celular e conferir o aviso com o bot desligado. Evite inserir o trecho duas vezes ou sobrepor outro botão flutuante. Apenas documentos publicados são consultados; trechos relevantes são enviados à Groq para gerar respostas.

`localhost` só funciona no computador de desenvolvimento, não no site público.
