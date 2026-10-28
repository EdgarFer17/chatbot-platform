"use client";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

export default function LoginPage() {
  const router = useRouter(); const [error, setError] = useState(""); const [loading, setLoading] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); setLoading(true); const form = new FormData(event.currentTarget);
    try {
    const response = await fetch("/api/auth/login", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ password: form.get("password") }), signal: AbortSignal.timeout(15000) });
    if (!response.ok) { const body = await response.json(); setError(body.detail ?? "Não foi possível entrar"); return; }
    router.replace("/"); router.refresh();
    } catch { setError("Não foi possível conectar. Tente novamente."); } finally { setLoading(false); }
  }
  return <main className="login-page"><section className="login-panel"><div className="login-brand"><div><b>FAFIC</b><small>Assistente institucional</small></div></div><div className="login-copy"><p>ACESSO À ADMINISTRAÇÃO</p><h1>Bem-vindo ao painel</h1><span>Entre para controlar o chatbot da faculdade.</span></div><form onSubmit={submit}><label>Senha<input name="password" type="password" autoComplete="current-password" required autoFocus /></label>{error && <p className="form-error" role="alert">{error}</p>}<button className="f-button" disabled={loading}>{loading ? "Entrando..." : "Entrar no painel"}</button></form></section></main>;
}
