// Run only with scripts.preview_fixture and the local QA admin server.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
(async () => {
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  try {
    const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
    const page = await context.newPage(); page.setDefaultTimeout(120000);
    const errors = []; page.on('pageerror', error => errors.push(error.message));
    const output = path.resolve('test-results'); fs.mkdirSync(output, { recursive: true });
    await page.goto('http://localhost:3100/'); await page.waitForURL('**/login');
    assert.equal(await page.locator('input').count(), 1);
    await page.getByLabel('Senha').fill('wrong-password');
    await page.getByRole('button', { name: 'Entrar no painel' }).click();
    await page.getByRole('alert').filter({ hasText: 'Senha incorreta' }).waitFor();
    await page.getByLabel('Senha').fill('local-qa-only');
    await page.getByRole('button', { name: 'Entrar no painel' }).click();
    await page.waitForURL('http://localhost:3100/');
    await page.getByRole('switch').waitFor();
    assert.equal(await page.locator('nav').count(), 1);
    const custom = 'Nosso bot está temporariamente indisponível. Use o contato de demonstração.';
    await page.getByLabel('Mensagem para quem está no site').fill(custom);
    await page.getByRole('button', { name: 'Salvar mensagem' }).click();
    await page.getByText('Mensagem salva.', { exact: true }).waitFor();
    await page.reload(); await page.getByRole('switch').waitFor();
    assert.equal(await page.getByLabel('Mensagem para quem está no site').inputValue(), custom);
    for (const width of [1440, 768, 390, 320]) {
      await page.setViewportSize({ width, height: 900 });
      assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'Horizontal overflow at ' + width);
      await page.screenshot({ path: path.join(output, `control-${width}.png`), fullPage: true });
    }
    await page.getByRole('switch').click();
    await page.getByRole('heading', { name: 'Chatbot desligado' }).waitFor();
    for (const route of ['/configuracoes','/testar','/clientes']) {
      await page.goto('http://localhost:3100' + route); await page.waitForURL('http://localhost:3100/');
    }
    async function mountWidget() {
      await page.goto('http://localhost:3100/');
      await page.setContent('<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"></head><body><h1>Demonstração local</h1><chatbot-platform api-url="http://localhost:8110"></chatbot-platform></body></html>');
      await page.addScriptTag({ url: 'http://localhost:3100/chatbot-widget.js', type: 'module' });
      await page.getByRole('button', { name: 'Abrir atendimento virtual' }).click();
      await page.waitForFunction(() => !document.querySelector('chatbot-platform').busy);
    }
    await mountWidget();
    await page.locator('chatbot-platform .assistant').filter({ hasText: custom }).waitFor();
    const controlUrl = 'http://localhost:3100/api/platform/institution/control';
    assert.equal((await context.request.patch(controlUrl, { data: { active: true } })).status(), 200);
    await mountWidget();
    await page.getByRole('textbox', { name: 'Mensagem' }).fill('Como faço a matrícula?');
    await page.getByRole('button', { name: 'Enviar mensagem' }).click();
    await page.locator('chatbot-platform .assistant p').filter({ hasText: 'portal acadêmico' }).first().waitFor();
    const answer = await page.locator('chatbot-platform .assistant .bubble > p').last().innerText();
    assert(!answer.includes('Com base em'));
    assert.equal(await page.locator('chatbot-platform .sources[open]').count(), 0);
    const session = await page.locator('chatbot-platform').evaluate(element => element.sessionId);
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.screenshot({ path: path.join(output, 'widget-natural-desktop.png'), fullPage: true });
    await mountWidget();
    assert.equal(await page.locator('chatbot-platform').evaluate(element => element.sessionId), session);
    await page.setViewportSize({ width: 390, height: 844 });
    await page.screenshot({ path: path.join(output, 'widget-natural-mobile.png'), fullPage: true });
    await context.request.patch(controlUrl, { data: { active: false } });
    await page.getByRole('textbox', { name: 'Mensagem' }).fill('Olá');
    await page.getByRole('button', { name: 'Enviar mensagem' }).click();
    await page.locator('chatbot-platform .assistant').filter({ hasText: custom }).waitFor();
    assert(await page.getByRole('button', { name: 'Enviar mensagem' }).isEnabled());
    await context.request.patch(controlUrl, { data: { active: true } });
    await page.route('http://localhost:8110/**', route => route.abort());
    await page.getByRole('textbox', { name: 'Mensagem' }).fill('Outra pergunta');
    await page.getByRole('button', { name: 'Enviar mensagem' }).click();
    await page.waitForFunction(() => !document.querySelector('chatbot-platform').busy);
    assert.equal(await page.locator('chatbot-platform .assistant .bubble > p').last().innerText(), custom);
    await page.unroute('http://localhost:8110/**');
    await page.goto('http://localhost:3100/'); await page.getByRole('button', { name: 'Sair', exact: true }).click();
    await page.waitForURL('**/login');
    assert.equal((await context.request.get(controlUrl)).status(), 401);
    assert.deepEqual(errors, []);
    console.log('PASS: password-only login, saved message, on/off, 320/390/768/1440px, natural widget replies, discreet sources, resume, custom outage message, network recovery, logout.');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exit(1); });
