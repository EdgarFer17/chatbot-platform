# Segurança e privacidade

## Princípios

1. Nenhum segredo é versionado.
2. Chaves de API são exibidas uma única vez e persistidas apenas como hash.
3. Toda consulta de negócio é limitada por tenant e ambiente.
4. A chave administrativa nunca é entregue ao navegador público.
5. Dados sensíveis são rejeitados ou sanitizados antes de logs e provedores externos.
6. Conteúdo documental só entra na recuperação depois de autorização.
7. Logs registram identificadores técnicos, não corpos de conversas, tokens ou documentos pessoais.

## Dados proibidos na V1

- Senhas e credenciais.
- Segredos de integração.
- Números de documentos pessoais sem necessidade formal.
- E-mails e telefones enviados como parte de perguntas livres.
- Dados acadêmicos individuais.

Caso a FAFIC necessite consultar informações pessoais de alunos, isso será um projeto separado, com autenticação do aluno, base legal, minimização e contrato específico.

## Ambientes

Homologação e produção utilizam chaves, dados, documentos e limites separados. Chaves terão prefixos identificáveis, como `cp_test_` e `cp_live_`, mas o valor completo nunca será armazenado ou logado.

## Navegador

Uma chave permanente não pode ser colocada no JavaScript da faculdade. A integração deverá usar o backend da instituição ou tokens de sessão públicos, curtos, limitados ao assistente e protegidos por origem e rate limit.

