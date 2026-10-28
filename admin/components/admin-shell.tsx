"use client";

import { Buildings, ChatCircle, Key, Robot, SignOut, Stack } from "@phosphor-icons/react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ReactNode } from "react";

const navigation = [
  { label: "Clientes", href: "/clientes", icon: Buildings },
  { label: "Assistentes", href: "/clientes", icon: Robot },
  { label: "Conhecimentos", href: "/clientes", icon: Stack },
  { label: "Conversas", href: "/clientes", icon: ChatCircle },
  { label: "Credenciais", href: "/clientes", icon: Key },
];

export function AdminShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  async function logout() { await fetch("/api/auth/logout", { method: "POST" }); window.location.href = "/login"; }
  return <div className="shell">
    <aside className="rail">
      <Link href="/clientes" className="wordmark"><span>cp</span><strong>Chatbot<br/>Platform</strong></Link>
      <nav>{navigation.map(item => <Link key={item.label} href={item.href} className={pathname.startsWith(item.href) && item.label === "Clientes" ? "active" : ""}><item.icon size={19}/><span>{item.label}</span></Link>)}</nav>
      <div className="rail-foot"><span className="live-dot"/><div><b>Local</b><small>serviços ativos</small></div></div>
    </aside>
    <main className="workbench">
      <header className="masthead"><div className="crumb">OPERAÇÃO <span>/</span> PLATAFORMA</div><div className="account"><div><b>Operador</b><small>administrador</small></div><span>OP</span><button className="logout" onClick={logout} title="Sair"><SignOut size={18}/></button></div></header>
      {children}
    </main>
  </div>;
}
