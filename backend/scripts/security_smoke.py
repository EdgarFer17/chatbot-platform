"""Non-destructive checks for common public deployment mistakes."""
import argparse
import json
import urllib.error
import urllib.request


def fetch(request: urllib.request.Request) -> tuple[int, dict[str, str], str]:
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.status, dict(response.headers), response.read().decode()
    except urllib.error.HTTPError as error:
        return error.code, dict(error.headers), error.read().decode()


def main() -> None:
    parser = argparse.ArgumentParser(description="Checagem de segurança HTTP")
    parser.add_argument("--base-url", default="http://127.0.0.1:8010")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    checks: list[tuple[str, bool]] = []
    status, _, _ = fetch(urllib.request.Request(f"{base}/v1/admin/tenants"))
    checks.append(("admin_requires_credential", status in {401, 422}))
    status, _, _ = fetch(urllib.request.Request(f"{base}/v1/sessions", data=b'{"assistant_id":"00000000-0000-0000-0000-000000000000"}', method="POST", headers={"Authorization": "Bearer cbp_invalid_key", "Content-Type": "application/json"}))
    checks.append(("invalid_api_key_rejected", status == 401))
    status, headers, _ = fetch(urllib.request.Request(f"{base}/v1/sessions", method="OPTIONS", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"}))
    checks.append(("untrusted_origin_not_allowed", "Access-Control-Allow-Origin" not in headers))
    status, _, body = fetch(urllib.request.Request(f"{base}/openapi.json"))
    checks.append(("openapi_available", status == 200))
    checks.append(("openapi_has_no_secrets", "local-admin-secret" not in body and "ADMIN_MASTER_KEY" not in body))
    result = {name: passed for name, passed in checks}
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if all(result.values()) else 1)


if __name__ == "__main__":
    main()
