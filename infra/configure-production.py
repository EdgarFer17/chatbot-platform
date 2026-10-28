"""Create a new production .env interactively; never overwrite existing settings."""
import getpass
import hashlib
import os
from pathlib import Path
import secrets
from urllib.parse import urlsplit


def main():
    destination = Path(__file__).resolve().parent.parent / ".env"
    if destination.exists():
        raise SystemExit("Já existe .env. Nenhum arquivo foi alterado. Revise a configuração existente.")
    domain = "chatbot.catolicapb.com.br"
    password = getpass.getpass("Nova senha do painel (mínimo 12 caracteres): ")
    if not 12 <= len(password) <= 1024:
        raise SystemExit("Senha deve ter entre 12 e 1024 caracteres.")
    if password != getpass.getpass("Confirme a senha: "):
        raise SystemExit("As senhas não conferem.")
    groq = getpass.getpass("Chave GROQ_API_KEY: ").strip()
    if not groq or any(c.isspace() for c in groq) or any(c in groq for c in "'\"$#"):
        raise SystemExit("Chave Groq vazia ou com caracteres inválidos.")
    extra = input("Origens HTTPS do site (separadas por vírgula; Enter para configurar depois): ").strip()
    origins = [f"https://{domain}"]
    for value in extra.split(","):
        value = value.strip().rstrip("/")
        if not value:
            continue
        parts = urlsplit(value)
        if (parts.scheme != "https" or not parts.hostname or parts.path or parts.query
                or parts.fragment or parts.username or parts.password
                or any(c.isspace() or c in "'\"$#" for c in value)):
            raise SystemExit("Origem inválida: use https://dominio sem caminho.")
        if value not in origins:
            origins.append(value)
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=32768, r=8, p=1,
                            dklen=64, maxmem=64 * 1024 * 1024)
    values = {
        "PANEL_DOMAIN": domain, "CADDY_CONFIG": "Caddyfile.single-domain",
        "PLATFORM_PUBLIC_API_URL": f"https://{domain}", "WIDGET_PUBLIC_URL": f"https://{domain}",
        "ALLOWED_ORIGINS": ",".join(origins),
        **{key: secrets.token_hex(32) for key in (
            "POSTGRES_PASSWORD", "JWT_SECRET_KEY", "ADMIN_MASTER_KEY", "ADMIN_SESSION_SECRET")},
        "ADMIN_PASSWORD_HASH": f"scrypt:{salt.hex()}:{digest.hex()}",
        "ADMIN_COOKIE_SECURE": "true", "GROQ_API_KEY": groq, "LLM_PROVIDER": "groq",
        "GROQ_MODEL": "openai/gpt-oss-20b", "LLM_MAX_OUTPUT_TOKENS": "700",
        "LLM_TIMEOUT_SECONDS": "35", "LLM_REASONING_EFFORT": "low",
    }
    fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
        stream.write("\n".join(f"{key}={value}" for key, value in values.items()) + "\n")
    print("Configuração criada. Senha armazenada somente como hash. Segredos não exibidos.")


if __name__ == "__main__":
    main()
