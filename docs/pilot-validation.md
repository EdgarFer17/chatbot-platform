# Validação do piloto

## Contrato público

- Versão candidata: `1.0.0-rc.1`.
- Especificação: `docs/openapi.json`.
- Swagger local: `http://127.0.0.1:8010/docs`.
- A integração pública precisa somente da chave `cbp_...`, do identificador do assistente e dos endpoints de sessão.

## Segurança HTTP

Execute sem modificar dados:

```powershell
backend/.venv/Scripts/python.exe backend/scripts/security_smoke.py
```

## Carga leve

O teste cria sessões e envia perguntas reais; portanto consome a cota do ambiente. Use homologação:

```powershell
backend/.venv/Scripts/python.exe backend/scripts/load_test.py `
  --api-key "COLE_A_CHAVE_CBP" `
  --assistant-id "COLE_O_ID_DO_ASSISTENTE" `
  --requests 20 `
  --concurrency 5
```

Para o piloto inicial, o resultado mínimo esperado é 100% de sucesso sem respostas 5xx. A latência depende do provedor de IA configurado e deve ser analisada separadamente para respostas extrativas e respostas geradas.

## Resultado registrado — 1º de setembro de 2026

Teste executado em homologação com 20 fluxos completos e concorrência 5:

- sucesso: 20 de 20 (100%);
- falhas: 0;
- mediana: 0,640 s;
- p95: 1,225 s;
- máxima: 1,227 s;
- respostas finais: 20 com HTTP 201;
- respostas 5xx: nenhuma.

O candidato `1.0.0-rc.1` atende ao critério inicial de carga do piloto. Esse
resultado representa uma carga leve de validação funcional e não substitui um
teste de capacidade progressiva antes de contratos com volume elevado.
