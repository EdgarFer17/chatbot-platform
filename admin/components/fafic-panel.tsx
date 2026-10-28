"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { ChatCircle, CheckCircle, WarningCircle, SignOut } from "@phosphor-icons/react";
import Link from "next/link";

type Control = { active: boolean; unavailable_message: string };
async function request(body?: Partial<Control>): Promise<Control> {
  const response = await fetch("/api/platform/institution/control", {
    method: body ? "PATCH" : "GET", headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined, signal: AbortSignal.timeout(15000),
  });
  if (response.status === 401) { window.location.assign("/login"); throw new Error("Entre novamente para continuar."); }
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Não foi possível salvar. Tente novamente.");
  return data;
}
const errorText = (error: unknown) => error instanceof Error && error.name === "Error" ? error.message : "Não foi possível conectar. Tente novamente em instantes.";

export function FaficPanel() {
  const [control, setControl] = useState<Control | null>(null);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const load = useCallback(async () => {
    setLoading(true); setError("");
    try { const data = await request(); setControl(data); setMessage(data.unavailable_message); }
    catch (reason) { setError(errorText(reason)); } finally { setLoading(false); }
  }, []);
  useEffect(() => { void load(); }, [load]);
  async function update(body: Partial<Control>, success: string) {
    setBusy(true); setError(""); setNotice("");
    try { const data = await request(body); setControl(data); if (body.unavailable_message !== undefined) setMessage(data.unavailable_message); setNotice(success); }
    catch (reason) { setError(errorText(reason)); } finally { setBusy(false); }
  }
  async function save(event: FormEvent) { event.preventDefault(); await update({ unavailable_message: message.trim() }, "Mensagem salva."); }
  async function logout() {
    try { await fetch("/api/auth/logout", { method: "POST" }); window.location.assign("/login"); }
    catch { setError("Não foi possível sair. Tente novamente."); }
  }
  return <div className="f-app"><header className="f-header"><div className="f-brand"><strong>FAFIC</strong><span>Assistente institucional</span></div><button className="f-logout" onClick={logout}><SignOut size={18}/>Sair</button></header><main className="f-control"><p className="f-eyebrow">CONTROLE DO ATENDIMENTO</p><h1>Seu chatbot, em um só lugar.</h1><p className="f-intro">Ligue ou desligue o assistente e defina o aviso de indisponibilidade.</p>
    <nav className="d-navigation" aria-label="Navegação do painel"><Link href="/" aria-current="page">Controle</Link><Link href="/documentos">Documentos</Link><Link href="/metricas">Métricas</Link><Link href="/conversas">Conversas</Link><a href="/demo.html" target="_blank" rel="noopener noreferrer">Testar chat ↗</a></nav>
    {error && <div className="f-alert error" role="alert"><WarningCircle size={21}/><span>{error}</span>{!control && <button onClick={() => void load()}>Tentar novamente</button>}</div>}
    {notice && <div className="f-alert success" role="status"><CheckCircle size={21}/>{notice}</div>}
    {loading ? <div className="f-loading" role="status">Carregando…</div> : control && <>
      <section className="f-status-card"><div className="f-chat-icon"><ChatCircle size={32}/></div><div className="f-status-copy"><h2>Chatbot {control.active ? "ligado" : "desligado"}</h2><p>{control.active ? "O assistente está habilitado para responder no site." : "O site exibirá a mensagem de indisponibilidade."}</p></div><button className={`f-toggle ${control.active ? "on" : ""}`} role="switch" aria-checked={control.active} aria-label="Chatbot ligado" disabled={busy} onClick={() => void update({ active: !control.active }, control.active ? "Chatbot desligado." : "Chatbot ligado.")}><span/></button></section>
      <form className="f-card" onSubmit={save}><h2>Mensagem de indisponibilidade</h2><p>Este aviso aparece quando o bot está desligado ou não consegue responder, inclusive quando o limite da IA é atingido.</p><label htmlFor="unavailable">Mensagem para quem está no site</label><textarea id="unavailable" rows={5} maxLength={1000} required value={message} onChange={event => setMessage(event.target.value)} placeholder="Nosso bot está temporariamente indisponível. Envie uma mensagem para…"/><div className="f-form-bottom"><span>Você pode incluir um telefone ou contato de WhatsApp.</span><button className="f-button" disabled={busy || !message.trim() || message.trim() === control.unavailable_message}>{busy ? "Salvando…" : "Salvar mensagem"}</button></div></form>
    </>}<footer>FAFIC · Assistente institucional</footer></main></div>;
}
