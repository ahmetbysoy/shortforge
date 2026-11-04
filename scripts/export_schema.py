"""Script JSON semasini docs/schemas/ altina yazar (LLM cikti dogrulamasi icin)."""

from __future__ import annotations

import json
from pathlib import Path

from shortforge.models import Script

TARGET = Path(__file__).resolve().parents[1] / "docs" / "schemas" / "script.schema.json"


def main() -> None:
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    schema = Script.model_json_schema()
    TARGET.write_text(json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"yazildi: {TARGET}")


if __name__ == "__main__":
    main()
