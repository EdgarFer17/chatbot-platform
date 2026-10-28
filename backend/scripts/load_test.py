"""Small dependency-free smoke load test for the public conversation API."""
import argparse
import json
import statistics
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed


def request_json(url: str, api_key: str, payload: dict) -> tuple[int, dict]:
    request = urllib.request.Request(url, data=json.dumps(payload).encode(), method="POST", headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read() or b"{}")


def run_user(base_url: str, api_key: str, assistant_id: str, index: int) -> tuple[bool, float, int]:
    started = time.perf_counter()
    status, session = request_json(f"{base_url}/v1/sessions", api_key, {"assistant_id": assistant_id, "external_user_id": f"load-test-{index}"})
    if status != 201:
        return False, time.perf_counter() - started, status
    status, _ = request_json(f"{base_url}/v1/sessions/{session['id']}/messages", api_key, {"content": "Quais informações institucionais estão disponíveis?"})
    return status == 201, time.perf_counter() - started, status


def main() -> None:
    parser = argparse.ArgumentParser(description="Teste leve de carga do fluxo público")
    parser.add_argument("--base-url", default="http://127.0.0.1:8010")
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--assistant-id", required=True)
    parser.add_argument("--requests", type=int, default=20)
    parser.add_argument("--concurrency", type=int, default=5)
    args = parser.parse_args()
    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        results = list(as_completed([executor.submit(run_user, args.base_url.rstrip("/"), args.api_key, args.assistant_id, index) for index in range(args.requests)]))
        values = [future.result() for future in results]
    durations = sorted(item[1] for item in values)
    percentile_index = max(0, min(len(durations) - 1, round(len(durations) * 0.95) - 1))
    succeeded = sum(1 for success, _, _ in values if success)
    codes: dict[int, int] = {}
    for _, _, code in values:
        codes[code] = codes.get(code, 0) + 1
    print(json.dumps({"requests": len(values), "succeeded": succeeded, "failed": len(values) - succeeded, "success_rate": round(succeeded / len(values) * 100, 2), "latency_seconds": {"median": round(statistics.median(durations), 3), "p95": round(durations[percentile_index], 3), "max": round(max(durations), 3)}, "status_codes": codes}, indent=2))
    raise SystemExit(0 if succeeded == len(values) else 1)


if __name__ == "__main__":
    main()
