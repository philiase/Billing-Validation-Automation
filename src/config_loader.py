from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_config(config_path: Path) -> dict[str, Any]:
    """Load validation settings from JSON so business rules are not hard-coded."""
    with config_path.open("r", encoding="utf-8") as config_file:
        return json.load(config_file)
