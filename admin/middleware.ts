import { NextRequest, NextResponse } from "next/server";
import { ADMIN_SESSION_COOKIE, verifyAdminSession } from "@/lib/admin-session";

export async function middleware(request: NextRequest) {
  const session = await verifyAdminSession(request.cookies.get(ADMIN_SESSION_COOKIE)?.value);
  if (request.nextUrl.pathname === "/login") return session ? NextResponse.redirect(new URL("/", request.url)) : NextResponse.next();
  if (!session) return NextResponse.redirect(new URL("/login", request.url));
  return NextResponse.next();
}
export const config = { matcher: ["/", "/documentos/:path*", "/testar/:path*", "/configuracoes/:path*", "/clientes/:path*", "/login"] };
