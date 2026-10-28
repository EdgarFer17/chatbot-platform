// Convert an existing local password without printing it or touching other settings.
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { parseEnv } from "node:util";
import { randomBytes, scryptSync } from "node:crypto";
import { resolve } from "node:path";
const target = resolve(process.argv[2] || "../.env");
if (!existsSync(target)) { console.log("Arquivo de ambiente não encontrado. Configure a senha com scripts/hash-password.mjs."); process.exit(0); }
const content = readFileSync(target, "utf8"), environment = parseEnv(content);
if (environment.ADMIN_PASSWORD_HASH) { console.log("Hash de senha já configurado; nenhuma alteração."); process.exit(0); }
if (!environment.ADMIN_PASSWORD) { console.log("Não há senha existente para converter. Configure a senha com scripts/hash-password.mjs."); process.exit(0); }
const salt = randomBytes(16), hash = scryptSync(environment.ADMIN_PASSWORD, salt, 64, { N: 32768, r: 8, p: 1, maxmem: 64 * 1024 * 1024 });
const updated = content.split(/\r?\n/).filter(line => !/^\s*(?:export\s+)?ADMIN_PASSWORD(?:_HASH)?\s*=/.test(line)).join("\n");
writeFileSync(target, `${updated.trimEnd()}\nADMIN_PASSWORD_HASH=scrypt:${salt.toString("hex")}:${hash.toString("hex")}\n`, { mode: 0o600 });
console.log("Senha existente convertida para hash. A senha de acesso continua a mesma.");
