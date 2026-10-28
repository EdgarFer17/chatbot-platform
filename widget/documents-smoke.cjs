// Disposable fixture only: backend/scripts/preview_fixture.py and admin at :3100.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
(async () => {
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  try {
    const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
    const page = await context.newPage(); page.setDefaultTimeout(120000);
    const errors=[]; page.on('pageerror', error => errors.push(error.message));
    await page.goto('http://localhost:3100/documentos');
    await page.getByLabel('Senha').fill('local-qa-only');
    await page.getByRole('button', { name: 'Entrar no painel' }).click();
    await page.waitForURL('http://localhost:3100/');
    await page.getByRole('link', { name: 'Documentos', exact: true }).click();
    await page.getByRole('heading', { name: 'Documentos do chatbot' }).waitFor();
    await page.getByText('Carregando documentos…').waitFor({state:'hidden'});
    await page.locator('input[type=file]').setInputFiles({name:'Biblioteca QA.txt',mimeType:'text/plain',buffer:Buffer.from('Documento fictício de teste. A biblioteca de demonstração abre às nove horas de segunda a sexta-feira.')});
    await page.getByText('Arquivo importado. Abra o conteúdo, revise e clique em Publicar documento.').waitFor();
    const row=page.locator('.d-document').filter({hasText:'Biblioteca QA.txt'});
    await row.getByRole('button',{name:'Abrir conteúdo'}).click();
    await page.getByRole('dialog').waitFor();
    assert((await page.getByRole('dialog').innerText()).includes('nove horas'));
    await page.getByRole('button',{name:'Publicar documento',exact:true}).click();
    await page.getByText('Documento publicado. Ele já pode ser usado pelo chatbot.').waitFor();
    assert.equal(await row.locator('.d-badge').innerText(),'Publicado');
    fs.mkdirSync('test-results',{recursive:true});
    for(const width of [1440,768,390,320]) {
      await page.setViewportSize({width,height:950});
      assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'Overflow '+width);
      await page.screenshot({path:`test-results/documents-restored-${width}.png`,fullPage:true});
    }
    // Read back through the same RAG without the administrative browser proxy.
    const answer=await context.request.post('http://127.0.0.1:8110/v1/admin/institution/preview',{headers:{'X-Admin-Key':'local-qa-only'},data:{content:'Qual o horário da biblioteca?'}});
    assert((await answer.json()).content.includes('nove horas'));
    await row.getByRole('button',{name:'Abrir conteúdo'}).click();
    await page.getByRole('button',{name:'Retirar das respostas'}).click();
    await page.getByText('Documento retirado das respostas.').waitFor();
    assert.equal(await row.locator('.d-badge').innerText(),'Aguardando revisão');
    await page.getByRole('button',{name:'Adicionar por URL'}).click();
    await page.getByLabel('Nome da fonte').fill('Fonte de demonstração');
    await page.getByLabel('Endereço público').fill('https://example.org/manual');
    await page.getByRole('button',{name:'Cancelar',exact:true}).click();
    await row.getByRole('button',{name:'Excluir',exact:true}).click();
    await page.getByRole('button',{name:'Cancelar',exact:true}).click();
    assert.equal(await row.count(),1);
    const source=page.locator('.d-source').filter({hasText:'Biblioteca QA.txt'});
    await source.getByRole('button',{name:'Excluir fonte'}).click();
    await page.getByRole('button',{name:'Excluir definitivamente'}).click();
    await page.getByText('Exclusão concluída.').waitFor();
    assert.equal(await row.count(),0);
    assert.deepEqual(errors,[]);
    console.log('PASS: upload, review, publish, RAG retrieval, unpublish, URL form, confirmation/cancellation, source deletion, 320/390/768/1440px.');
  } finally { await browser.close(); }
})().catch(error=>{console.error(error);process.exit(1);});
