import { copyFileSync, existsSync, mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
const source = fileURLToPath(new URL("../../widget/chatbot-widget.js", import.meta.url));
const target = fileURLToPath(new URL("../public/chatbot-widget.js", import.meta.url));
if (existsSync(source)) { mkdirSync(fileURLToPath(new URL("../public/", import.meta.url)), { recursive: true }); copyFileSync(source, target); }
else if (!existsSync(target)) throw new Error("O arquivo público do widget não está disponível.");
const demo = fileURLToPath(new URL("../../widget/demo.html", import.meta.url));
if (existsSync(demo)) copyFileSync(demo, fileURLToPath(new URL("../public/demo.html", import.meta.url)));
