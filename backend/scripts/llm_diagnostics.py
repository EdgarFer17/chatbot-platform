"""Validates the configured Groq model without printing credentials."""
import json

import httpx

from app.core.config import settings


def main() -> None:
    result = {
        "provider": settings.llm_provider,
        "api_key_configured": bool(settings.groq_api_key),
        "model": settings.groq_model,
        "model_available": False,
        "generation_ok": False,
    }
    if settings.llm_provider != "groq" or not settings.groq_api_key:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        raise SystemExit(1)

    headers = {"Authorization": f"Bearer {settings.groq_api_key}"}
    try:
        model_response = httpx.get(
            f"https://api.groq.com/openai/v1/models/{settings.groq_model}",
            headers=headers,
            timeout=settings.llm_timeout_seconds,
        )
        result["model_available"] = model_response.status_code == 200
        if result["model_available"]:
            completion = httpx.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json={
                    "model": settings.groq_model,
                    "temperature": 0,
                    "max_completion_tokens": 256,
                    "reasoning_effort": "low",
                    "include_reasoning": False,
                    "messages": [{"role": "user", "content": "Responda apenas: OK"}],
                },
                timeout=settings.llm_timeout_seconds,
            )
            completion.raise_for_status()
            result["generation_ok"] = bool(completion.json()["choices"][0]["message"]["content"].strip())
    except (httpx.HTTPError, KeyError, IndexError, TypeError) as error:
        result["error_type"] = type(error).__name__

    print(json.dumps(result, indent=2, ensure_ascii=False))
    raise SystemExit(0 if result["model_available"] and result["generation_ok"] else 1)


if __name__ == "__main__":
    main()
