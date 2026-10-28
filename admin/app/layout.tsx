import type { Metadata } from "next";
import "./login.css";
import "./institution.css";
export const metadata: Metadata = { title: "FAFIC — Assistente institucional", description: "Painel administrativo do assistente da FAFIC" };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) { return <html lang="pt-BR"><body>{children}</body></html>; }
