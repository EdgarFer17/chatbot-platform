"use client";

import Link from "next/link";
import { FormEvent, ReactNode, useCallback, useEffect, useRef, useState } from "react";

type Document = { id: string; title: string; content?: string; status: "draft" | "published"; is_current: boolean; version_number: number };
type Source = { id: string; name: string; source_type: string; last_synced_at: string | null; last_error: string | null; sync_status: string };
type Job = { status: string; processed: number; discovered: number; error_message: string | null; failed: number };
async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`/api/platform/institution${path}`, { ...options, signal: AbortSignal.timeout(55000) });
  if (response.status === 401) { window.location.assign("/login"); throw new Error("Entre novamente para continuar."); }
  const data = response.status === 204 ? null : await response.json();
  if (!response.ok) throw new Error(typeof data?.detail === "string" ? data.detail : "Não foi possível concluir. Verifique os dados e tente novamente.");
  return data;
}
function Modal({ title, children, close }: { title: string; children: ReactNode; close: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => { dialog.current?.showModal(); }, []);
  return <dialog ref={dialog} className="d-dialog" aria-labelledby="document-dialog-title" onCancel={event => { event.preventDefault(); close(); }}><header><h2 id="document-dialog-title">{title}</h2><button onClick={close} aria-label="Fechar">×</button></header>{children}</dialog>;
}

export function DocumentsPanel() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [sources, setSources] = useState<Source[]>([]);
  const [jobs, setJobs] = useState<Record<string, Job | null>>({});
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [review, setReview] = useState<Document | null>(null);
  const [adding, setAdding] = useState(false);
  const [removal, setRemoval] = useState<{ id: string; title: string; kind: "documents" | "sources" } | null>(null);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("all");
  const fileInput = useRef<HTMLInputElement>(null);
  const reload = useCallback(async () => {
    const [docs, items] = await Promise.all([api<Document[]>("/documents"), api<Source[]>("/sources")]);
    const progress = await Promise.all(items.filter(item => item.source_type !== "file" && item.source_type !== "manual").map(async item => [item.id, await api<Job | null>(`/sources/${item.id}/job`)] as const));
    setDocuments(docs); setSources(items); setJobs(Object.fromEntries(progress));
  }, []);
  const report = (reason: unknown) => setError(reason instanceof Error && reason.name === "Error" ? reason.message : "Não foi possível conectar. Tente novamente em instantes.");
  useEffect(() => { reload().catch(report).finally(() => setLoading(false)); }, [reload]);
  const processing = Object.values(jobs).some(job => job && ["pending", "running"].includes(job.status));
  useEffect(() => {
    if (!processing) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;
    const poll = async () => { try { await reload(); } catch (reason) { if (!cancelled) report(reason); } finally { if (!cancelled) timer = setTimeout(poll, 4000); } };
    timer = setTimeout(poll, 4000);
    return () => { cancelled = true; clearTimeout(timer); };
  }, [processing, reload]);
  async function act(work: () => Promise<unknown>, success: string) {
    setBusy(true); setError(""); setNotice("");
    try { await work(); await reload(); setNotice(success); } catch (reason) { report(reason); } finally { setBusy(false); }
  }
  async function upload(file?: File) {
    if (!file) return;
    if (file.size > 20 * 1024 * 1024) { setError("O arquivo excede o limite de 20 MB."); return; }
    const data = new FormData(); data.set("file", file);
    await act(() => api("/sources/upload", { method: "POST", body: data }), "Arquivo importado. Abra o conteúdo, revise e clique em Publicar documento.");
  }
  async function addSource(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const data = new FormData(event.currentTarget);
    await act(async () => {
      const source = await api<Source>("/sources", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name: data.get("name"), source_url: data.get("url"), source_type: data.get("type") }) });
      setAdding(false);
      await api(`/sources/${source.id}/sync`, { method: "POST" });
    }, "Fonte adicionada. Aguarde o processamento e revise os documentos antes de publicar.");
  }
  const visible = documents.filter(item => (item.is_current || item.status === "published") && item.title.toLocaleLowerCase().includes(search.toLocaleLowerCase()) && (filter === "all" || item.status === filter));
  const published = documents.filter(item => item.status === "published").length;
  const drafts = documents.filter(item => item.is_current && item.status === "draft").length;
  const dialogError = error ? <p className="f-alert error" role="alert">{error}</p> : null;
  return <div className="f-app"><header className="f-header"><Link className="f-brand" href="/"><strong>FAFIC</strong><span>Assistente institucional</span></Link><Link href="/" className="f-logout">Voltar ao controle</Link></header><main className="f-control d-page"><p className="f-eyebrow">BASE DE CONHECIMENTO</p><h1>Documentos do chatbot</h1><p className="f-intro">Envie os documentos, revise o conteúdo e publique as informações que o bot pode usar.</p><nav className="d-navigation" aria-label="Navegação do painel"><Link href="/">Controle</Link><Link href="/documentos" aria-current="page">Documentos</Link><Link href="/metricas">Métricas</Link><Link href="/conversas">Conversas</Link><a href="/demo.html" target="_blank" rel="noopener noreferrer">Testar chat ↗</a></nav>
    {error && !review && !adding && !removal && <div className="f-alert error" role="alert">{error}<button disabled={busy} onClick={() => void act(reload, "Lista atualizada.")}>Tentar novamente</button></div>}{notice && <div className="f-alert success" role="status">{notice}</div>}
    {loading ? <p role="status" className="f-loading">Carregando documentos…</p> : <><section className="d-overview"><span><strong>{published}</strong> publicados</span><span><strong>{drafts}</strong> aguardando revisão</span><span>Somente os publicados entram nas respostas.</span></section>{!published && <div className="f-alert error">O chatbot ainda não tem documentos publicados. Envie um arquivo e publique após revisar.</div>}
    <div className="d-toolbar"><button className="f-button" disabled={busy} onClick={() => fileInput.current?.click()}>{busy ? "Processando…" : "Enviar arquivo"}</button><input ref={fileInput} hidden type="file" accept=".pdf,.docx,.txt,.html,.htm" onChange={event => { void upload(event.target.files?.[0]); event.target.value = ""; }}/><button className="f-button d-secondary" disabled={busy} onClick={() => { setError(""); setAdding(true); }}>Adicionar por URL</button><small>PDF, DOCX, TXT e HTML · Até 20 MB</small></div>
    <section className="f-card d-documents"><div className="d-section-heading"><h2>Revisão e publicação</h2><button className="d-link" disabled={busy} onClick={() => void act(reload, "Lista atualizada.")}>Atualizar lista</button></div><div className="d-filters"><label>Buscar documento<input value={search} onChange={event => setSearch(event.target.value)} placeholder="Digite o título…"/></label><label>Situação<select value={filter} onChange={event => setFilter(event.target.value)}><option value="all">Todos</option><option value="draft">Aguardando revisão</option><option value="published">Publicados</option></select></label></div>{!visible.length ? <p className="d-empty">Nenhum documento encontrado.</p> : visible.map(item => <article className="d-document" key={item.id}><div><h3>{item.title}</h3><p>Versão {item.version_number}{!item.is_current ? " · Continua nas respostas até a aprovação da nova versão" : ""}</p><span className={`d-badge ${item.status}`}>{item.status === "published" ? "Publicado" : "Aguardando revisão"}</span></div><div className="d-actions"><button className="f-button d-secondary" disabled={busy} onClick={() => void act(async () => setReview(await api<Document>(`/documents/${item.id}`)), "")}>Abrir conteúdo</button><button className="d-delete" disabled={busy} onClick={() => { setError(""); setRemoval({ id: item.id, title: item.title, kind: "documents" }); }}>Excluir</button></div></article>)}</section>
    <section className="f-card d-sources"><h2>Fontes e sincronização</h2>{!sources.length && <p>Nenhuma fonte cadastrada.</p>}{sources.map(source => { const job = jobs[source.id]; const working = Boolean(job && ["pending", "running"].includes(job.status)); return <article className="d-source" key={source.id}><div><h3>{source.name}</h3><p>{working ? `Processando ${job!.processed} de ${job!.discovered || "…"}` : `Última sincronização: ${source.last_synced_at ? new Date(source.last_synced_at).toLocaleString("pt-BR") : "ainda não realizada"}`}</p>{working && <progress value={job!.processed} max={Math.max(job!.discovered, 1)} aria-label="Progresso da sincronização"/>}{(source.last_error || job?.error_message) && <p className="d-error">{source.last_error || job?.error_message}</p>}</div><div className="d-actions">{["website", "document_url"].includes(source.source_type) && <button className="f-button d-secondary" disabled={busy || working} onClick={() => void act(() => api(`/sources/${source.id}/sync`, { method: "POST" }), "Sincronização iniciada.")}>{working ? "Processando…" : "Sincronizar"}</button>}<button className="d-delete" disabled={busy || working} onClick={() => { setError(""); setRemoval({ id: source.id, title: source.name, kind: "sources" }); }}>Excluir fonte</button></div></article>; })}</section></>}
    </main>
    {adding && <Modal title="Adicionar fonte por URL" close={() => !busy && setAdding(false)}><form className="d-form" onSubmit={addSource}><label>Nome da fonte<input name="name" minLength={3} maxLength={220} required/></label><label>Endereço público<input name="url" type="url" required placeholder="https://…"/></label><label>Importar<select name="type"><option value="document_url">Somente esta página ou arquivo</option><option value="website">Site e páginas internas</option></select></label><p>O conteúdo será importado como rascunho para revisão.</p>{dialogError}<footer><button type="button" className="f-button d-secondary" disabled={busy} onClick={() => setAdding(false)}>Cancelar</button><button className="f-button" disabled={busy}>{busy ? "Adicionando…" : "Adicionar e processar"}</button></footer></form></Modal>}
    {review && <Modal title={review.title} close={() => !busy && setReview(null)}><div className="d-form"><p>Confira o texto extraído antes de disponibilizá-lo nas respostas.</p><pre>{review.content}</pre>{dialogError}<footer><button className="f-button d-secondary" disabled={busy} onClick={() => setReview(null)}>Fechar</button><button className="f-button" disabled={busy} onClick={() => void act(async () => { await api(`/documents/${review.id}/${review.status === "published" ? "unpublish" : "publish"}`, { method: "POST" }); setReview(null); }, review.status === "published" ? "Documento retirado das respostas." : "Documento publicado. Ele já pode ser usado pelo chatbot.")}>{review.status === "published" ? "Retirar das respostas" : "Publicar documento"}</button></footer></div></Modal>}
    {removal && <Modal title="Confirmar exclusão" close={() => !busy && setRemoval(null)}><div className="d-form"><p>Excluir <strong>{removal.title}</strong>?</p><p>{removal.kind === "sources" ? "A fonte e todos os documentos vinculados serão removidos. Esta ação não pode ser desfeita pelo painel." : "O documento será removido. Esta ação não pode ser desfeita pelo painel."}</p>{dialogError}<footer><button className="f-button d-secondary" disabled={busy} onClick={() => setRemoval(null)}>Cancelar</button><button className="f-button d-danger" disabled={busy} onClick={() => void act(async () => { await api(`/${removal.kind}/${removal.id}`, { method: "DELETE" }); setRemoval(null); }, "Exclusão concluída.")}>Excluir definitivamente</button></footer></div></Modal>}
  </div>;
}
