import { NextRequest, NextResponse } from "next/server";
import { ADMIN_SESSION_COOKIE, verifyAdminSession } from "@/lib/admin-session";
const API_URL = process.env.PLATFORM_API_URL ?? "http://127.0.0.1:8010";

async function proxy(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  if (!await verifyAdminSession(request.cookies.get(ADMIN_SESSION_COOKIE)?.value)) return NextResponse.json({ detail: "Sessão expirada" }, { status: 401 });
  const { path } = await context.params;
  const route = path.join("/");
  const id = "[0-9a-fA-F-]{36}";
  const allowed = (request.method === "GET" && new RegExp(`^institution/(control|documents|documents/${id}|sources|sources/${id}/job|metrics|conversations|conversations/${id})$`).test(route))
    || (request.method === "PATCH" && route === "institution/control")
    || (request.method === "POST" && new RegExp(`^institution/(sources|sources/upload|sources/${id}/sync|documents/${id}/(publish|unpublish))$`).test(route))
    || (request.method === "DELETE" && new RegExp(`^institution/(sources|documents)/${id}$`).test(route));
  if (!allowed) return NextResponse.json({ detail: "Operação indisponível" }, { status: 404 });
  const adminKey = process.env.ADMIN_MASTER_KEY;
  if (!adminKey) return NextResponse.json({ detail: "Painel sem credencial administrativa" }, { status: 503 });
  const target = `${API_URL}/v1/admin/${path.join("/")}${request.nextUrl.search}`;
  const body = ["GET", "HEAD"].includes(request.method) ? undefined : await request.arrayBuffer();
  const contentType = request.headers.get("content-type");
  const headers: Record<string,string> = { "X-Admin-Key": adminKey };
  if (contentType) headers["Content-Type"] = contentType;
  try {
    const response = await fetch(target, { method: request.method, headers, body, cache: "no-store", signal: AbortSignal.timeout(50000) });
    return new NextResponse(response.body, { status: response.status, headers: { "Content-Type": response.headers.get("Content-Type") ?? "application/json", "Cache-Control": "no-store" } });
  } catch {
    return NextResponse.json({ detail: "O serviço está temporariamente indisponível. Tente novamente em instantes." }, { status: 503 });
  }
}
export const GET = proxy;
export const POST = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
