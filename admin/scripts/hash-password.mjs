import { randomBytes, scryptSync } from "node:crypto";
import { emitKeypressEvents } from "node:readline";

if (!process.stdin.isTTY) throw new Error("Execute este comando em um terminal interativo.");
process.stdout.write("Nova senha do painel (não será exibida): ");
emitKeypressEvents(process.stdin); process.stdin.setRawMode(true); process.stdin.resume();
let password = "";
process.stdin.on("keypress", (text, key) => {
  if (key?.ctrl && key.name === "c") process.exit(1);
  if (key?.name === "return") {
    process.stdin.setRawMode(false); process.stdin.pause();
    if (password.length < 12) { process.stderr.write("\nUse pelo menos 12 caracteres.\n"); process.exitCode = 1; return; }
    const salt = randomBytes(16);
    const hash = scryptSync(password, salt, 64, { N: 32768, r: 8, p: 1, maxmem: 64 * 1024 * 1024 });
    password = "";
    process.stdout.write(`\nADMIN_PASSWORD_HASH=scrypt:${salt.toString("hex")}:${hash.toString("hex")}\n`);
  } else if (key?.name === "backspace") password = password.slice(0, -1);
  else if (text && !key?.ctrl && !key?.meta && password.length < 1024) password += text;
});
