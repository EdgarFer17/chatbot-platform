"use client";

import { ArrowRight, Buildings, MagnifyingGlass, Plus, X } from "@phosphor-icons/react";
import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";

type Tenant = { id:string; name:string; slug:string; active:boolean; created_at:string };

export function ClientsPage() {
  const [clients,setClients] = useState<Tenant[]>([]);
  const [query,setQuery] = useState("");
  const [modal,setModal] = useState(false);
  const [error,setError] = useState("");

  const load = useCallback(async () => {
    const response = await fetch("/api/platform/tenants");
    if (response.ok) setClients(await response.json());
  }, []);
  useEffect(() => { void load(); }, [load]);

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError("");
    const form = new FormData(event.currentTarget);
    const response = await fetch("/api/platform/tenants", { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({name:form.get("name"),slug:form.get("slug")}) });
    if (!response.ok) { const body=await response.json(); setError(body.detail ?? "Não foi possível cadastrar"); return; }
    setModal(false); await load();
  }

  const filtered = clients.filter(client => `${client.name} ${client.slug}`.toLowerCase().includes(query.toLowerCase()));
  return <div className="page">
    <div className="title-row"><div><p className="kicker">CARTEIRA DE CLIENTES</p><h1>Instituições</h1><p className="subtitle">Cada cliente opera com dados, assistentes e credenciais isolados.</p></div><button className="action" onClick={()=>setModal(true)}><Plus size={17}/>Adicionar instituição</button></div>
    <div className="index-line"><b>{String(clients.length).padStart(2,"0")}</b><span>instituições cadastradas</span><i/><div className="search"><MagnifyingGlass size={17}/><input value={query} onChange={event=>setQuery(event.target.value)} placeholder="Filtrar instituições"/></div></div>
    <section className="institution-list">{filtered.map((client,index)=><Link href={`/clientes/${client.id}`} className="institution-row" key={client.id}><span className="sequence">{String(index+1).padStart(2,"0")}</span><div className="institution-monogram">{client.name.slice(0,2).toUpperCase()}</div><div className="institution-name"><h2>{client.name}</h2><p>{client.slug}</p></div><div className="state"><i/>{client.active?"Operando":"Pausado"}</div><div className="created"><small>CADASTRO</small><span>{new Date(client.created_at).toLocaleDateString("pt-BR")}</span></div><ArrowRight size={20}/></Link>)}</section>
    {modal && <div className="overlay"><section className="dialog"><header><span><Buildings size={19}/></span><div><p>NOVA INSTITUIÇÃO</p><h2>Adicionar cliente</h2></div><button onClick={()=>setModal(false)}><X size={19}/></button></header><form onSubmit={create}><label>Nome<input name="name" required minLength={2} placeholder="Nome oficial ou nome curto"/></label><label>Identificador técnico<input name="slug" required pattern="[a-z0-9]+(?:-[a-z0-9]+)*" placeholder="faculdade-exemplo"/><small>Será usado internamente e não poderá conter espaços.</small></label>{error&&<p className="form-error">{error}</p>}<footer><button type="button" className="quiet" onClick={()=>setModal(false)}>Cancelar</button><button className="action">Cadastrar</button></footer></form></section></div>}
  </div>;
}
