export const ADMIN_SESSION_COOKIE = "chatbot_platform_admin";
const SESSION_TTL_SECONDS = 60 * 60 * 8;

function secret() {
  const value = process.env.ADMIN_SESSION_SECRET;
  if (!value) throw new Error("ADMIN_SESSION_SECRET não configurado");
  return value;
}

function base64Url(bytes: ArrayBuffer) {
  return btoa(String.fromCharCode(...new Uint8Array(bytes))).replaceAll("+", "-").replaceAll("/", "_").replaceAll("=", "");
}

function encodePayload(value: string) {
  return btoa(unescape(encodeURIComponent(value))).replaceAll("+", "-").replaceAll("/", "_").replaceAll("=", "");
}

function decodePayload(value: string) {
  const normalized = value.replaceAll("-", "+").replaceAll("_", "/");
  return decodeURIComponent(escape(atob(normalized)));
}

async function signature(payload: string) {
  const encoder = new TextEncoder();
  const key = await crypto.subtle.importKey("raw", encoder.encode(secret()), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  return base64Url(await crypto.subtle.sign("HMAC", key, encoder.encode(payload)));
}

export async function createAdminSession(username: string) {
  const payload = encodePayload(JSON.stringify({ username, expiresAt: Math.floor(Date.now() / 1000) + SESSION_TTL_SECONDS }));
  return `${payload}.${await signature(payload)}`;
}

export async function verifyAdminSession(token?: string) {
  if (!token) return null;
  const [payload, suppliedSignature] = token.split(".");
  if (!payload || !suppliedSignature) return null;
  if (suppliedSignature !== await signature(payload)) return null;
  try {
    const data = JSON.parse(decodePayload(payload)) as { username: string; expiresAt: number };
    return data.expiresAt > Math.floor(Date.now() / 1000) ? data : null;
  } catch { return null; }
}

export const adminSessionMaxAge = SESSION_TTL_SECONDS;
