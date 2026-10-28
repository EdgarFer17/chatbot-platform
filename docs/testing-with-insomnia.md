# Testes manuais com Insomnia

Importe `docs/insomnia/chatbot-platform-insomnia.json` no Insomnia. A coleção já
contém a URL local e a chave administrativa usada apenas pelo Docker de
desenvolvimento. A execução Docker publica esta plataforma em
`http://127.0.0.1:8010`, preservando a porta 8000 para os outros projetos.

Execute as pastas na ordem numérica:

1. verifique a saúde da API;
2. crie a FAFIC e copie o campo `id` para `tenant_id` no ambiente do Insomnia;
3. crie homologação e copie seu `id` para `environment_id`;
4. crie e liste o assistente;
5. crie a chave do site e guarde o campo `key`, pois ele só é exibido uma vez;
6. copie o `id` da chave para `api_key_id` caso queira testar a revogação.
7. guarde a chave completa em `api_key`, crie uma sessão pública e copie o `id`
   retornado para `session_id` antes de enviar mensagens.

As pastas 06 a 08 permitem revisar documentos, conferir consumo e auditoria e
baixar o contrato OpenAPI. O limite mensal pode ser ajustado em homologação para
validar a resposta `429`.

Respostas esperadas: `200` em consultas, `201` em criações, `204` na revogação,
`401` para chaves inválidas, `409` para sessão encerrada e `429` ao atingir a cota.
Uma chamada administrativa sem `X-Admin-Key` ou com valor incorreto deve falhar.
As chamadas públicas usam `Authorization: Bearer cbp_...` e nunca recebem
`tenant_id` ou `environment_id` do site cliente.

O valor administrativo incluído na coleção é exclusivamente local. Antes da
primeira publicação, ele será substituído por um segredo forte no `.env` e a
coleção de produção não deverá conter esse segredo.
