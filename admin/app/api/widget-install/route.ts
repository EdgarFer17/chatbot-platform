import { NextRequest, NextResponse } from "next/server";
import { ADMIN_SESSION_COOKIE, verifyAdminSession } from "@/lib/admin-session";

export async function GET(request: NextRequest) {
  if (!await verifyAdminSession(request.cookies.get(ADMIN_SESSION_COOKIE)?.value)) return NextResponse.json({ detail: "Sessão expirada" }, { status: 401 });
  const escape = (text: string) => text.replaceAll("&", "&amp;").replaceAll('"', "&quot;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
  const site = escape((process.env.WIDGET_PUBLIC_URL || request.nextUrl.origin).replace(/\/$/, ""));
  const api = escape((process.env.PLATFORM_PUBLIC_API_URL || "http://localhost:8010").replace(/\/$/, ""));
  return NextResponse.json({ code: `<script type="module" src="${site}/chatbot-widget.js"></script>\n<chatbot-platform api-url="${api}"></chatbot-platform>` });
}
