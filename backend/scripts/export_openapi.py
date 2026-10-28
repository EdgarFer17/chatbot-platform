import json
from pathlib import Path

from app.main import app


def main() -> None:
    target = Path(__file__).resolve().parents[2] / "docs" / "openapi.json"
    target.write_text(json.dumps(app.openapi(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OpenAPI exportado para {target}")


if __name__ == "__main__":
    main()
