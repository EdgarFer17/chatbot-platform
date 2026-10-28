import { scrypt, timingSafeEqual } from "node:crypto";

export async function verifyAdminPassword(password: unknown, encoded: string): Promise<boolean> {
  if (typeof password !== "string" || !password || password.length > 1024) return false;
  const [scheme, salt, hash, extra] = encoded.split(":");
  if (scheme !== "scrypt" || extra || !/^[a-f0-9]{32}$/.test(salt ?? "") || !/^[a-f0-9]{128}$/.test(hash ?? "")) return false;
  const expected = Buffer.from(hash, "hex");
  const derived = await new Promise<Buffer>((resolve, reject) => {
    scrypt(password, Buffer.from(salt, "hex"), 64, { N: 32768, r: 8, p: 1, maxmem: 64 * 1024 * 1024 }, (error, result) => error ? reject(error) : resolve(result));
  });
  return timingSafeEqual(expected, derived);
}
