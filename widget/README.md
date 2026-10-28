# Widget da FAFIC

Insira este trecho no site, substituindo os dois endereços pelos endereços publicados do painel e da API:

```html
<script type="module" src="https://PAINEL-DA-FAFIC/chatbot-widget.js"></script>
<chatbot-platform api-url="https://API-DA-FAFIC"></chatbot-platform>
```

Não é necessário criar um endpoint no servidor do site para o fluxo institucional novo. O próprio backend emite tokens temporários vinculados à origem e à conversa. Nenhuma chave da Groq ou chave permanente de integração é enviada ao navegador.

## Configuração do servidor

- Configure `ALLOWED_ORIGINS` com a origem exata do site, por exemplo `https://www.SEUDOMINIO.edu.br`. Autorize também a variante sem `www` caso seja utilizada. Reinicie o backend após mudar a configuração.
- Vincule o assistente usando `scripts.setup_fafic` e publique sua documentação pela seção Documentos do painel.
- Configure a Groq no backend. Ligue o chatbot no painel.
- Use HTTPS no site, painel e API quando publicados.
- Caso o site tenha uma política CSP, permita o endereço do painel em `script-src`, o endereço da API em `connect-src` e os estilos necessários ao componente.

## Comportamento

O botão abre uma conversa. As respostas são texto normal, sem cabeçalho com o nome do documento. Uma opção “Ver fontes”, inicialmente fechada, permite consultar a origem quando necessário.

A conversa é mantida durante a navegação na mesma aba, com token renovável de 15 minutos e acesso de retomada de até 24 horas. “Nova conversa” inicia uma sessão separada. Se o armazenamento do navegador estiver bloqueado, a sessão funciona em memória enquanto a página estiver aberta.

Quando o chatbot está desligado ou a Groq falha, a mensagem configurada no painel aparece no chat. A última mensagem de indisponibilidade conhecida também é reutilizada em falhas de conexão. Em uma primeira visita com o backend totalmente fora do ar, o componente ainda não consegue buscar essa configuração: usa o aviso padrão ou o atributo `unavailable-message` informado pelo desenvolvedor.

## Opções facultativas do componente

```html
<chatbot-platform
  api-url="https://API-DA-FAFIC"
  title="Assistente FAFIC"
  welcome-message="Olá! Como posso ajudar?"
  accent-color="#173b73"
  unavailable-message="Nosso bot está temporariamente indisponível."
></chatbot-platform>
```

A paleta usa azul `#173b73` e dourado `#d9b45b`; os tons podem ser ajustados ao manual de marca da faculdade. Os atributos de apresentação são opcionais. A mensagem recebida do servidor prevalece sobre o aviso local de contingência.

## Teste local

Com a API em `http://localhost:8010`, autorize `http://localhost:4173` no backend e execute:

```powershell
cd widget
python -m http.server 4173
```

Abra http://localhost:4173/demo.html. Não é necessário colar tokens.

O fluxo legado com `assistant-id` e `token-endpoint` continua compatível para integrações existentes. O atributo `token` aceita somente tokens temporários `wgt_`, nunca chaves permanentes.

O arquivo original é `widget/chatbot-widget.js`; `npm run dev` e `npm run build` do painel sincronizam automaticamente a cópia pública.
