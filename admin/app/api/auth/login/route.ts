import { NextRequest, NextResponse } from "next/server";
import { ADMIN_SESSION_COOKIE, adminSessionMaxAge, createAdminSession } from "@/lib/admin-session";
import { verifyAdminPassword } from "@/lib/admin-password";

export const runtime = "nodejs";
let attempts: number[] = [];

export async function POST(request: NextRequest) {
  const { password = "" } = await request.json().catch(() => ({}));
  const stored = process.env.ADMIN_PASSWORD_HASH;
  if (!stored || !process.env.ADMIN_SESSION_SECRET) return NextResponse.json({ detail: "O acesso ainda não foi configurado pelo responsável pela instalação." }, { status: 503 });
  const now = Date.now(); attempts = attempts.filter(time => time > now - 60000);
  if (attempts.length >= 10) return NextResponse.json({ detail: "Aguarde um minuto antes de tentar novamente." }, { status: 429, headers: { "Retry-After": "60" } });
  attempts.push(now);
  if (!await verifyAdminPassword(password, stored)) return NextResponse.json({ detail: "Senha incorreta." }, { status: 401 });
  const response = NextResponse.json({ ok: true });
  response.cookies.set(ADMIN_SESSION_COOKIE, await createAdminSession("admin"), { httpOnly: true, sameSite: "strict", secure: process.env.ADMIN_COOKIE_SECURE === "true", path: "/", maxAge: adminSessionMaxAge });
  return response;
}
